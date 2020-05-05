# Redis-Wrapper
If you call a slow python function more than once using the same arguments, just wrap it with @redis_wrapper to cache previous values to Redis and make it go faster next time.

### Example:
~~~~
@redis_wrapper()
def my_slow_func(n):
  ... slow stuff happens here ...
  return foo
 

 x  = my_slow_func(5) # this is slow, but it caches its result to Redis
 x  = my_slow_func(5) # this is blazing fast!
 x2 = my_slow_func(7) # this is slow- it has a new argument and needs to recalculate
 x  = my_slow_func(5) # still blazing fast!
 x2 = my_slow_func(7) # now I'm blazing fast too!
~~~~

## max_age

If you are concerned about old, outdated values, you can apply a "max_age" kwarg to your decorator to ignore values cached more than max_age ago:

~~~~
@redis_wrapper(max_age="25 min")
def my_slow_func(n):
  ... slow stuff happens here ...
  return foo
  
 x  = my_slow_func(5) # this is slow, but it caches its result to Redis
 x  = my_slow_func(5) # this is blazing fast!
 ... a long time passes ...
 x  = my_slow_func(5) # slow again- gotta replace the old, stale value
 ~~~~
 
## recalc_key

If previously cached values become irrelevent not via the passage of time but by known, triggering events, you can use the recalc_key kwarg to check that trigger prior to using a cached value. Set the trigger with `set_recalc_key(recalc_key)`:

~~~~
@redis_wrapper(max_age="25 min", recalc_key="foo_changed")
def my_slow_func(n):
  ... slow stuff happens here ...
  return foo
  
 x  = my_slow_func(5) # this is slow, but it caches its result to Redis
 x  = my_slow_func(5) # this is blazing fast!
 set_recalc_key("foo_changed")
 x  = my_slow_func(5) # this is slow- an event made my old value invalid
 x  = my_slow_func(5) # this is blazing fast!
 set_recalc_key("something_else_changed")
 x  = my_slow_func(5) # this is blazing fast! I care about foo_changed, not something_else_changed

 ~~~~

## Installing Redis

If you are on Linux and don't have Redis installed, you could run something like
~~~~
$ docker pull redis:6.0.1
$ docker run -d -p6379:6379 --name MyRedis redis:6.0.1
~~~~
