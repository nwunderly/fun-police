
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
# r.set('www.youtube.com/watch?v=REWyCy_m39Q', 'bar')


# print(r.get('youtube.com/watch?v=REWyCy_m39Q'))
# b'bar'

for key in r.scan_iter():
    print(key)
    if len(key.decode()) < 5:
        print(' - deleting and replacing.')
        value = r.get(key)
        r.delete(key)

print('\n\n\n')

# for key in r.scan_iter():
#     print(key)
