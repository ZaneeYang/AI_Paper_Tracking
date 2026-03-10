"""
定时任务：每天在指定时间（默认 8:00）执行一次 run_daily.run()。
使用 APScheduler 的 CronTrigger，需保持进程常驻。
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import SCHEDULE_HOUR, SCHEDULE_MINUTE
from run_daily import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def job():
    logger.info("开始执行每日论文拉取与总结")
    try:
        run(output_format="markdown", save_to_file=True)
    except Exception as e:
        logger.exception("每日任务执行失败: %s", e)


def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(
        job,
        CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        id="daily_ai_papers",
    )
    logger.info("定时任务已启动，每天 %02d:%02d 执行", SCHEDULE_HOUR, SCHEDULE_MINUTE)
    scheduler.start()


if __name__ == "__main__":
    main()
