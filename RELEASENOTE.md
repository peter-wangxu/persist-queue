# 1.0.0-alpha

1. Only Python3.x series are offically supported by persistqueue, since Python 2 was no longer under maintenance since 2020

2. `persistqueue.Queue` using `serializer=persistqueue.serializers.pickle` created under python2 was no longer able to be read by persist queue after 1.0.0
   as the default pickle version changed from `2` to `4`

