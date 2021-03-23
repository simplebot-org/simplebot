import logging.handlers
import os

from ..hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser) -> None:
    parser.add_generic_option(
        "--stdlog",
        choices=["info", "debug", "err", "warn"],
        default="info",
        help="stdout logging level.",
        inipath="log:stdlog",
    )


@deltabot_hookimpl
def deltabot_get_logger(args) -> logging.Logger:
    loglevel = getattr(logging, args.stdlog.upper())
    return make_logger(args.basedir, loglevel)


def make_logger(logdir, stdout_loglevel) -> logging.Logger:
    logger = logging.Logger("simplebot")
    logger.parent = None
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    chandler = logging.StreamHandler()
    chandler.setLevel(stdout_loglevel)
    chandler.setFormatter(formatter)
    logger.addHandler(chandler)

    log_path = os.path.join(logdir, "bot.log")
    fhandler = logging.handlers.RotatingFileHandler(
        log_path, backupCount=5, maxBytes=2000000
    )
    fhandler.setLevel(logging.DEBUG)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)

    return logger


def test_logger_loglevel(capfd, tmpdir):
    logger = make_logger(tmpdir.strpath, stdout_loglevel=logging.INFO)
    logger.info("hello")
    logger.debug("world")
    out, err = capfd.readouterr()
    assert "hello" in err
    assert "world" not in err
