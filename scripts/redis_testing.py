import redis

r = redis.Redis(host='localhost', port=6379, db=0)
# r.set('www.youtube.com/watch?v=REWyCy_m39Q', 'bar')


# print(r.get('youtube.com/watch?v=REWyCy_m39Q'))
# b'bar'

for key in r.scan_iter():
    key = key.decode()
    print(key)
    item = eval(r.get(key).decode())
    print(item)
    if item['extra'] == key:
        print("REMOVING")
        r.delete(key)

print('\n\n\n')

# for key in r.scan_iter():
#     print(key)
