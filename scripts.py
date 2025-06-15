#!/usr/bin/env python
"""Point of entry"""
import sys
from scripts.deploy import deploy, build_image


class ManagementUtility:
    """Utility class to manage command-line execution."""

    def __init__(self, argv=None):
        self.argv = argv or sys.argv[:]

    def execute(self):
        try:
            subcommand = self.argv[1]
        except IndexError:
            subcommand = 'help' # Default to 'help' if no command is provided
        if subcommand == 'build_image':
            build_image()
        elif subcommand == 'deploy':
            deploy()
        elif subcommand == 'help':
            print("Available commands:")
            print("build_image")
            print("deploy")
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
