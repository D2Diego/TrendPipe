import ast
import copy
import threading
from abc import ABC, abstractmethod

from app.config import config
from app.models import const


_PATCH_EXISTING_TASK_SCRIPT = """
if redis.call("EXISTS", KEYS[1]) == 0 then
    return 0
end

for index = 1, #ARGV, 2 do
    redis.call("HSET", KEYS[1], ARGV[index], ARGV[index + 1])
end

return 1
"""


# Base class for state management
class BaseState(ABC):
    @abstractmethod
    def update_task(self, task_id: str, state: int, progress: int = 0, **kwargs):
        pass

    @abstractmethod
    def get_task(self, task_id: str):
        pass

    @abstractmethod
    def get_all_tasks(self, page: int, page_size: int):
        pass

    @abstractmethod
    def patch_task(self, task_id: str, **kwargs) -> bool:
        """Patch an existing task, returning False when it does not exist."""
        pass


# Memory state management
class MemoryState(BaseState):
    def __init__(self):
        self._tasks = {}
        self._lock = threading.RLock()

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        with self._lock:
            tasks = [copy.deepcopy(task) for task in self._tasks.values()]
            total = len(tasks)
        return tasks[start:end], total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "state": state,
                "progress": progress,
                **kwargs,
            }

    def get_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id, None)
            return copy.deepcopy(task) if task is not None else None

    def patch_task(self, task_id: str, **kwargs) -> bool:
        # Asynchronous publishing adds status without overwriting saved results.
        # Check existence and merge under one lock to avoid recreating deletions.
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.update(copy.deepcopy(kwargs))
            return True

    def delete_task(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)


# Redis state management
class RedisState(BaseState):
    """
    Redis-backed task state.

    Trust boundary: Redis is expected to be private to this application. Task
    values are written by TrendPipe and converted back from strings for
    compatibility with existing state records. Do not expose this Redis database
    to untrusted writers without replacing deserialization with a stricter
    schema-based format.
    """

    def __init__(self, host="localhost", port=6379, db=0, password=None):
        import redis

        self._redis = redis.StrictRedis(host=host, port=port, db=db, password=password)

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        tasks = []
        cursor = 0
        total = 0
        while True:
            # Redis also contains the RedisTaskManager list. Scan only hashes to
            # avoid WRONGTYPE and count only actual task records.
            cursor, keys = self._redis.scan(
                cursor,
                count=page_size,
                _type="HASH",
            )
            batch_start = total
            batch_size = len(keys)
            total += batch_size

            # SCAN returns batches. Slice from the current batch's starting index
            # rather than the accumulated total to keep pagination correct.
            if batch_start < end and total > start:
                slice_start = max(0, start - batch_start)
                slice_end = min(batch_size, end - batch_start)
                for key in keys[slice_start:slice_end]:
                    task_data = self._redis.hgetall(key)
                    task = {
                        k.decode("utf-8"): self._convert_to_original_type(v)
                        for k, v in task_data.items()
                    }
                    tasks.append(task)

            # Continue to cursor=0 even after filling the page so total is exact.
            if cursor == 0:
                break
        return tasks, total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        fields = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }

        for field, value in fields.items():
            self._redis.hset(task_id, field, str(value))

    def get_task(self, task_id: str):
        task_data = self._redis.hgetall(task_id)
        if not task_data:
            return None

        task = {
            key.decode("utf-8"): self._convert_to_original_type(value)
            for key, value in task_data.items()
        }
        return task

    def patch_task(self, task_id: str, **kwargs) -> bool:
        if not kwargs:
            return False

        arguments = []
        for field, value in kwargs.items():
            arguments.extend((field, str(value)))

        # An atomic Lua script prevents HSET from recreating a task concurrently
        # deleted between separate EXISTS and HSET commands.
        updated = self._redis.eval(
            _PATCH_EXISTING_TASK_SCRIPT,
            1,
            task_id,
            *arguments,
        )
        return bool(updated)

    def delete_task(self, task_id: str):
        self._redis.delete(task_id)

    @staticmethod
    def _convert_to_original_type(value):
        """
        Convert values written by this application back to common Python types.

        This compatibility parser assumes Redis is inside the application's
        trust boundary. If Redis can be written by untrusted clients, task state
        should move to a strict JSON/schema parser instead of open-ended literal
        conversion.
        """
        value_str = value.decode("utf-8")

        try:
            # try to convert byte string array to list
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            pass

        if value_str.isdigit():
            return int(value_str)
        # Add more conversions here if needed
        return value_str


# Global state
_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)

state = (
    RedisState(
        host=_redis_host, port=_redis_port, db=_redis_db, password=_redis_password
    )
    if _enable_redis
    else MemoryState()
)
