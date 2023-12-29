class URIBuilder(object):
    def __init__(self, base_uri):
        self.uri = base_uri

    def add_parameter(self, key, value):
        if value:
            self.uri += '&{}={}'.format(str(key), str(value))

    def get_uri(self):
        return self.uri
