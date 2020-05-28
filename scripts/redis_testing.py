
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
# r.set('www.youtube.com/watch?v=REWyCy_m39Q', 'bar')


# print(r.get('youtube.com/watch?v=REWyCy_m39Q'))
# b'bar'

for key in r.scan_iter():
    print(key)
    if key.decode().startswith('www.'):
        print(' - deleting and replacing.')
        value = r.get(key)
        r.delete(key)
        r.set(key.decode().replace('www.', ''), value)

print('\n\n\n')

for key in r.scan_iter():
    print(key)
