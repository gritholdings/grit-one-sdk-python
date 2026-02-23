#!/usr/bin/env python
import sys
from scripts.deploy import deploy, build_image
from scripts.deploy_azure import deploy as deploy_azure, build_image as build_image_azure


class ManagementUtility:
    def __init__(self, argv=None):
        self.argv = argv or sys.argv[:]
    def execute(self):
        try:
            subcommand = self.argv[1]
        except IndexError:
            subcommand = 'help'
        if subcommand == 'build_image':
            build_image()
        elif subcommand == 'deploy':
            deploy()
        elif subcommand == 'build_image_azure':
            build_image_azure()
        elif subcommand == 'deploy_azure':
            deploy_azure()
        elif subcommand == 'help':
            print("Available commands:")
            print("build_image")
            print("deploy")
            print("build_image_azure")
            print("deploy_azure")
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
