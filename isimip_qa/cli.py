import argparse
import re

from isimip_utils.cli import parse_parameters, parse_path

placeholder_pattern = re.compile(r'^.*?=.*?$')

class ArgumentAction(argparse.Action):

    def __call__(self, parser, args, values, option_string=None):
        for value in values:
            match = placeholder_pattern.match(value)
            if match:
                try:
                    args.placeholders.update(parse_parameters(value))
                except AttributeError:
                    args.placeholders = parse_parameters(value)
            else:
                try:
                    args.paths.append(parse_path(value))
                except AttributeError:
                    args.paths = [parse_path(value)]
