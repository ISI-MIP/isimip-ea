import argparse
import re

from isimip_utils.cli import parse_parameters, parse_path

parameter_pattern = re.compile(r'^.*?=.*?$')


class ArgumentAction(argparse.Action):

    def __call__(self, parser, args, values, option_string=None):
        for value in values:
            match = parameter_pattern.match(value)
            if match:
                try:
                    args.parameters.update(parse_parameters(value))
                except AttributeError:
                    args.parameters = parse_parameters(value)
            else:
                try:
                    args.paths.append(parse_path(value))
                except AttributeError:
                    args.paths = [parse_path(value)]
