# Redis-Wrapper
If you call a slow python function more than once using the same arguments, just wrap it with @redis_wrapper to cache previous values to Redis and make it go faster next time.

# Example:
@redis_wrapper()
def my_slow_func(n):
  ... slow stuff happens here ...
  return foo
 
 x1 = my_slow_func(5) # this is slow, but it caches its result to Redis
 x1 = my_slow_func(5) # this is blazing fast!
 x2 = my_slow_func(7) # this is slow- it has a new argument and needs to recalc
 x1 = my_slow_func(5) # still blazing fast!
 x2 = my_slow_func(7) # now I'm fast too
