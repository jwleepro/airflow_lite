import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m airflow_lite <command>")
        print("Commands: service [install|remove|start|stop]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "service":
        import win32serviceutil
        from airflow_lite.service.win_service import AirflowLiteService
        win32serviceutil.HandleCommandLine(AirflowLiteService)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
