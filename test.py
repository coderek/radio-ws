import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

l = logging.getLogger('name')

def test():
    l.error(Exception("wrong"))

test()
