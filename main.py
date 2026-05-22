from src.utils.m_log import f_log, f_log_execution, setup_logging


def main() -> None:
    setup_logging()
    f_log_execution("{{ project_name }}", start=True)

    f_log("{{ project_name }} started", level="start")

    f_log_execution("{{ project_name }}", start=False)


if __name__ == "__main__":
    main()
