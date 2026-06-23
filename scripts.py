#!/usr/bin/env python
import sys
from scripts.deploy import detect_provider, deploy, build_image


class ManagementUtility:
    def __init__(self, argv=None):
        self.argv = argv or sys.argv[:]
    def _get_option(self, name):
        prefix = f"{name}="
        for arg in self.argv[2:]:
            if arg.startswith(prefix):
                return arg[len(prefix):]
        return None
    def execute(self):
        try:
            subcommand = self.argv[1]
        except IndexError:
            subcommand = 'help'
        if subcommand == 'build_image':
            provider = detect_provider()
            build_image(provider)
        elif subcommand == 'deploy':
            target = self._get_option('--target')
            if target:
                print(f"Deploy target: {target}")
            provider = detect_provider()
            deploy(provider)
        elif subcommand == 'help':
            print("Available commands:")
            print("build_image")
            print("deploy [--target=<name>]")
            print("help")
        else:
            print(f"Unknown command: {subcommand}")
            print("Please use 'help' to see available commands.")


def execute_from_command_line(argv=None):
    utility = ManagementUtility(argv)
    utility.execute()


def main():
    execute_from_command_line(sys.argv)
if __name__ == '__main__':
    main()
