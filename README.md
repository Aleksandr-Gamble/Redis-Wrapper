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
 x  = my_slow_func(5) # fast again!
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

## Setting up Redis on Docker

This application assumes you have two Redis instances running- one with AOF append-only persistence and one with ephemeral memory only. 
Here is how you can accomplish this with Docker:

# pull the image
sudo docker pull redis:6.01


Ephemeral Redis
# nothing gets persisted
sudo lsof -i :6379  # ensure the port is open
sudo docker run \
     -d -p6379:6379 \
     --name Redis.Ephemeral redis:6.0.1


Persisted Redis
# every write is recorded immutably and replayed on restart
sudo lsof -i :7379  # ensure the port is open
# Folder permissions are funky here: this seems to work:
sudo chmod a+rwx dvAOF           # everybody can write
sudo chown -R root:root dvAOF    # docker runs as root
sudo docker run \
     -d -p7379:6379 \
     -v $HOME/Redis-Wrapper/dvAOF:/data \
     --name Redis.Persisted redis:6.0.1 --appendonly yes
