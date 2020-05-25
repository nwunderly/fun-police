
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
r.set('foo', 'bar')


print(r.get('foo'))
# b'bar'

for key in r.scan_iter():
    print(key)




