"""Allow running as `python -m etoro_agent <command>`."""
import warnings
warnings.simplefilter("ignore")

from .cli import main

if __name__ == "__main__":
    main()
