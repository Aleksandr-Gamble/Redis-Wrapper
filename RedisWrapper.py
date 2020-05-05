
import redis, json, time

redis_cache = redis.Redis()



def set_recalc_key(recalc_key):
    # Set the "trigger" recalc_key in Redis so any methods that rely on it are forced to recalculate
    redis_cache.set('rc_key@{}'.format(recalc_key), 1)



def string_to_seconds(s):
    # given a string of the format 2, 2s, 2min, 3Hours, etc., return the number of seconds
    s = ''.join(str(s).lower())
    num = float(''.join([ char for char in s if char.isnumeric() or char == '.']))
    multiplier = 1
    for k,v in {'h':60*60,'m':60,'hr':60*60,'min':60,'hour':60*60,'minute':60,'d':24*60*60,'day':24*60*60}.items():
        if k in s:
            multiplier = v
            break 
    return num * multiplier



def object_to_sort_string(x):
    # recursively decompose x into a sorted string
    if type(x).__name__ == 'dict':
        return '--'.join([ '{}_{}'.format(object_to_sort_string(k),object_to_sort_string(x[k])) for k in sorted(list(x.keys()))])
    elif type(x).__name__ in ['set','tuple','list']:
        # make the key differentiate between feeding it a set, tuple, or list
        return type(x).__name__ +'.'+ '-'.join([object_to_sort_string(y) for y in list(x) ])
    else: # string, int, real, bool
        return str(x)



def redis_wrapper(max_age=None, recalc_key=None, verbose=False):
    # This wrapper is applied when you are defining a function you want to speed up with Redis
    # if the same function has been called with the same args and kwargs before, the calculation will be skipped and a cached version from Redis returned
    # if a combination of (function, args, kwargs) is new, the function will be called and the value stored in Redis for the next time
    # NOTE value will be re-calculated and Redis update if either of these conditions are True:
    #    max_age: it has been < max_age since the value was last updated (to avoid stale data)
    #    recalc_key: an event has triggerd a "recalculation key" indicating the old value is no longer valid
    def cache_decorator(func):
        def wrapper(*args, **kwargs):

            # Generate a key based on the (function, args, kwargs)
            key = func.__name__ + '-' + '_'.join([ object_to_sort_string(x) for x in ( list(args) + sorted(list(kwargs.items())) ) ] )
            key_type = '{}@type@'.format(key)
            key_updated = '{}@updated@'.format(key)


            # determine if a recalculation is needed
            recalc = False # assume it is not to start
            val = redis_cache.get(key) # try to get the key
            if val == None:
                # no value was found for this key in Redis- a recalc is needed
                recalc = True
            else:
                # A value was found in Redis, but is it current?
                if max_age != None:
                    # The user has specified a maximum age beofre stored values are "stale"
                    last_updated = redis_cache.get(key_updated)
                    if last_updated != None:
                        # the value has been stored previously in Redis
                        last_updated = float(last_updated.decode('utf-8'))
                        if time.time() - last_updated > string_to_seconds(max_age):
                            # the stored value is too old
                            recalc = True
                if recalc_key != None:
                    # The user specified this function should check for a trigger indicating the old value is invalid
                    trigger_status = redis_cache.get('rc_key@{}'.format(recalc_key))
                    if trigger_status != None:
                        # A value has been stored for the trigger
                        trigger_status = int(trigger_status.decode('utf-8'))
                        if trigger_status == 1:
                            # The trigger is set to true: a recalc is needed
                            recalc = True


            # perform the calculation if needed...
            if recalc:
                # The value did not exist in the Redis cache. Call the function
                val = func(*args, **kwargs)
                val_type = type(val).__name__
                val_updated = int(time.time()) # timestamp in seconds
                # update Redis with the new value
                if val_type in ('set', 'tuple'):
                    redis_cache.set(key, json.dumps(list(val)))
                elif val_type in ['dict','list']:
                    redis_cache.set(key, json.dumps(val))
                elif val_type == 'bool':
                    redis_cache.set(key, str(val))
                else:
                    redis_cache.set(key, val)
                redis_cache.set(key_type, val_type) # record the type of value
                redis_cache.set(key_updated, val_updated) # record when it was updated
                if recalc_key != None:
                    # indicate the value has been updated- no more recalculation needed
                    redis_cache.set('rc_key@{}'.format(recalc_key), 0)
                if verbose:
                    print('Redis SET {} = {}'.format(key, val))
                

            # ... or format the value stored in Redis
            else:
                # The value did exist in the Redis cache
                val_type = redis_cache.get(key_type).decode('utf-8')
                if val_type == 'set':
                    val = set(json.loads(val.decode('utf-8')))
                elif val_type == 'tuple':
                    val =  tuple(json.loads(val.decode('utf-8')))
                elif val_type in ['list', 'dict']:
                    val =  json.loads(val.decode('utf-8'))
                elif val_type == 'str':
                    val =  val.decode('utf-8')
                elif val_type == 'float':
                    val =  float(val)
                elif val_type == 'int':
                    val =  int(val)
                elif val_type == 'bool':
                    val = ('true' in val.decode('utf-8').lower())
                else:
                    val = val
                if verbose:
                    print('Redis GET {} = {}'.format(key, val))

            return val      # the function you create returns a value...
        return wrapper      # the wrapper alters that function...
    return cache_decorator  # redis_wrapper returns a decorator that creates that wrapper

