class OptionParser(object):
    def __init__(self):
        self._opts = {}

    def add_option(self, opt, opt_value, opt_type, default):
        self._opts['-{}'.format(opt)] = {'opt_value': opt_value, 'opt_type': opt_type, 'default': default}

    def parse(self, inputs: list):
        options = {value['opt_value']: value['default'] for key, value in self._opts.items()}

        for i, option in enumerate(inputs):
            if option not in self._opts:
                continue

            if self._opts[option]['opt_type']:
                value = inputs[i+1]
                if not isinstance(value, self._opts[option]['opt_type']) or value in self._opts:
                    return False
                del inputs[i:i+2]
            else:
                value = True
                del inputs[i]

            options[self._opts[option]['opt_value']] = value

        return inputs, options


