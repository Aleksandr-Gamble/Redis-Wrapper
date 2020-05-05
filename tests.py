from RedisWrapper import *
import pytest



@redis_wrapper(max_age='3s', recalc_key='rc_test', verbose=True)
def dummy_slow_square(*args, **kwargs):
    print('oh crap! this function squares an integer but is really slow...')
    time.sleep(1)
    return args[0]**2

def test_redis_int():
    redis_cache.delete("dummy_slow_square_3")
    t0 = time.time()
    val1 = dummy_slow_square(3) # could be slow
    t1 = time.time()
    val2 = dummy_slow_square(3) # should be fast
    t2 = time.time()
    assert val1 == val2
    assert (t2 - t1) < 0.1      # ensure it was fast (used the cache)
    print('Verified dummy_slow_square in {:.5f}s (func call) -> {:.5f}s (Redis cache)'.format(t1-t0, t2-t1))
    set_recalc_key('rc_test')
    val3 = dummy_slow_square(3) # should be slow
    t3 = time.time()
    assert val2 == val3
    assert (t3 - t2) > 0.9      # ensure it was slow (triggered recalc)
    print('PASSED test_redis_int')
    



@redis_wrapper(max_age='3s', recalc_key='rc_test', verbose=True)
def dummy_slow_json(*args, **kwargs):
    print('oh crap! this function returns JSON but is really slow...')
    time.sleep(1)
    return {'foo':'bar'}

def test_redis_json():
    redis_cache.delete("dummy_slow_json_color-blue_hot-False")
    t0 = time.time()
    val1 = dummy_slow_json(**{'color':'blue','hot':False})
    t1 = time.time()
    val2 = dummy_slow_json(**{'hot':False, 'color':'blue'}) # note the order of kwargs is reversed
    t2 = time.time()
    print(type(val1), type(val2))
    print(val1, val2)
    assert val1 == val2
    assert (t2 - t1) < 0.1 # should be fast
    print('Waiting...')
    time.sleep(4)
    t3 = time.time()
    val3 = dummy_slow_json(**{'hot':False, 'color':'blue'}) 
    t4 = time.time()
    assert val2 == val3
    assert (t4 - t3) > 0.8 # should be fast with a max_age recalc
    print('Verified dummy_slow_square in {:.5f}s (func call) -> {:.5f}s (Redis cache)'.format(t1-t0, t2-t1))
    print('PASSED test_redis_json')




@redis_wrapper(verbose=True)
def cache_and_pass(x):
    return x

def test_types():
    global x, x2, x3
    for x in [False, 'Stringy',3,(1,3,'fish'),set([1,3,'fish']),[1,3,'fish'], {'color':'blue', 'verdict':True}]:
        x2 = cache_and_pass(x)
        x3 = cache_and_pass(x)
        assert x == x2 == x3
        print('PASSED type test with',x)


test_redis_int()
test_redis_json()
test_types()
print('CONGRATULATIONS! Passed all tests.')
