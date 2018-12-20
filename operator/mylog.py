import logging

class Logger(object):
    def __init__(self, filename):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.fh = logging.FileHandler(filename, mode='a')
        self.fh.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
        self.fh.setFormatter(self.formatter)
        self.logger.addHandler(self.fh)

    def debug(self, msg):
        self.logger.debug(msg)
