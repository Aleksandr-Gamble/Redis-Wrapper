
import redis, json, time

redis_ephemeral = redis.Redis(port=6379)
redis_persisted = redis.Redis(port=7379)



def set_recalc_key(recalc_key, persisted_inst=False):
    # Set the "trigger" recalc_key in Redis so any methods that rely on it are forced to recalculate
    if persisted_inst:
        redis_inst = redis_persisted
    else:
        redis_inst = redis_ephemeral
    invalid_before = float(time.time()) # entries before this timestamp will be considered invalid
    redis_inst.set('rc_key@{}'.format(recalc_key), invalid_before )



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



def redis_wrapper(max_age=None, recalc_key=None, persisted_inst=False, verbose=False):
    # This wrapper is applied when you are defining a function you want to speed up with Redis
    # if the same function has been called with the same args and kwargs before, the calculation will be skipped and a cached version from Redis returned
    # if a combination of (function, args, kwargs) is new, the function will be called and the value stored in Redis for the next time
    # NOTE value will be re-calculated and Redis update if either of these conditions are True:
    #    max_age: it has been < max_age since the value was last updated (to avoid stale data)
    #    recalc_key: an event has triggerd a "recalculation key" indicating the old value is no longer valid
    if persisted_inst:
        redis_inst = redis_persisted
    else:
        redis_inst = redis_ephemeral
    def cache_decorator(func):
        def wrapper(*args, **kwargs):

            # Generate a key based on the (function, args, kwargs)
            key_base = func.__name__ + '-' + '_'.join([ object_to_sort_string(x) for x in ( list(args) + sorted(list(kwargs.items())) ) ] )
            key_Primary = '{}@Primary'.format(key_base)     # this key stores the object you are caching
            key_DatType = '{}@DatType'.format(key_base)     # this key notes its type
            key_SetTime = '{}@SetTime'.format(key_base)     # this key notes when it was updated 
            key_GetCount = '{}@GetCount'.format(key_base)   # this key counts how many times it has been read


            # determine if a recalculation is needed
            recalc = False # assume it is not to start
            val_Primary = redis_inst.get(key_Primary) # try to get the key
            if val_Primary == None:
                # no value was found for this key in Redis- a recalc is needed
                recalc = True
            else:
                # A value was found in Redis, but is it current?
                if max_age != None:
                    # The user has specified a maximum age beofre stored values are "stale"
                    last_updated = redis_inst.get(key_SetTime)
                    if last_updated != None:
                        # the value has been stored previously in Redis
                        last_updated = float(last_updated.decode('utf-8'))
                        if time.time() - last_updated > string_to_seconds(max_age):
                            # the stored value is too old
                            recalc = True
                if recalc_key != None:

                    # The user specified this function should check for a trigger indicating the old value is invalid
                    invalid_before = redis_inst.get('rc_key@{}'.format(recalc_key)) # a timestamp invalidating previous entries
                    val_SetTime = redis_inst.get(key_SetTime) # the timestamp of the last entry
                    print('**I HAS RECALC inv_before={}, val_SetTime={}'.format(invalid_before, val_SetTime))
                    if (invalid_before != None) and (val_SetTime != None):
                        # A invalid_before tirgger is stored and a previous item was cahced
                        invalid_before = float(invalid_before)
                        val_SetTime = float(val_SetTime)
                        if invalid_before > val_SetTime:
                            # The trigger is set to true: a recalc is needed
                            recalc = True


            # perform the calculation if needed...
            if recalc:
                # The value did not exist in the Redis cache. Call the function
                # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                val_Primary = func(*args, **kwargs) # <<<--- HERE IS WHERE YOU CALL THE FUNCTION YOU WRAPPED IN @redis_wrapper
                # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                val_DatType = type(val_Primary).__name__
                val_SetTime = float(time.time()) # timestamp in seconds
                # update Redis with the new value
                if val_DatType in ('set', 'tuple'):
                    redis_inst.set(key_Primary, json.dumps(list(val_Primary)))
                elif val_DatType in ['dict','list']:
                    redis_inst.set(key_Primary, json.dumps(val_Primary))
                elif val_DatType == 'bool':
                    redis_inst.set(key_Primary, str(val_Primary))
                else:
                    redis_inst.set(key_Primary, val_Primary)
                redis_inst.set(key_DatType, val_DatType) # record the type of value
                redis_inst.set(key_SetTime, val_SetTime) # record when it was updated
                redis_inst.set(key_GetCount, 0)          # this new value has not been read yet
                if verbose:
                    print('Redis SET {}'.format(key_Primary))
                

            # ... or format the value stored in Redis
            else:
                # The value did exist in the Redis cache
                val_DatType = redis_inst.get(key_DatType).decode('utf-8')
                if val_DatType == 'set':
                    val_Primary = set(json.loads(val_Primary.decode('utf-8')))
                elif val_DatType == 'tuple':
                    val_Primary =  tuple(json.loads(val_Primary.decode('utf-8')))
                elif val_DatType in ['list', 'dict']:
                    val_Primary =  json.loads(val_Primary.decode('utf-8'))
                elif val_DatType == 'str':
                    val_Primary =  val_Primary.decode('utf-8')
                elif val_DatType == 'float':
                    val_Primary =  float(val_Primary)
                elif val_DatType == 'int':
                    val_Primary =  int(val_Primary)
                elif val_DatType == 'bool':
                    val_Primary = ('true' in val_Primary.decode('utf-8').lower())
                else:
                    val_Primary = val_Primary
                redis_inst.incr(key_GetCount)
                if verbose:
                    print('Redis GET {}'.format(key_Primary))

            return val_Primary      # the function you create returns a value...
        return wrapper      # the wrapper alters that function...
    return cache_decorator  # redis_wrapper returns a decorator that creates that wrapper

