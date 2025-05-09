import redis

REQUEST_LIMIT = 10
TIME_WINDOW = 60

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
