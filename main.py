from colorama import init, Fore, Style
from config import api_hash, api_id, logger_chat_id, logger_token
from telegram import TGLogger
from pyrogram import Client
import traceback
import argparse
import asyncio
import logging
import os
workdir = os.path.join(os.getcwd(), "sessions")
os.makedirs(workdir, exist_ok=True)
init(autoreset=True)

app = Client("session", api_id=api_id, api_hash=api_hash, workdir=workdir)
logger = logging.getLogger(__name__)
tg_logger = TGLogger(logger_token, logger_chat_id)
async def main():
  parser = argparse.ArgumentParser(
    description="Telegram autobuy-bot CLI: snipe gifts by criteria",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument(
    "--id",
    type=int,
    help=(
      "Only target gift(s) with this unique ID "
      "(scans default/all gifts if omitted)"
    )
  )
  parser.add_argument(
    "--title",
    type=str,
    help=(
      "Only target gifts whose title matches exactly "
      "(case-sensitive string comparison)"
    )
  )
  parser.add_argument(
    "-n",
    dest="nullable_title",
    action="store_true",
    help=(
      "Allow gift entries with no title (skip title filter) "
      "if no title is present"
    )
  )
  parser.add_argument(
    "--price",
    type=int,
    help=(
      "Only target gifts with exactly this price "
      "(in TGStars)"
    )
  )
  parser.add_argument(
    "--total_amount",
    type=int,
    help=(
      "Only target gifts that have exactly this total available amount"
    )
  )
  parser.add_argument(
    "--check_every",
    type=int,
    default=60,
    metavar="SECS",
    help=(
      "Poll for new gifts every N seconds "
      "(default: %(default)s)"
    )
  )
  parser.add_argument(
    "--amount",
    type=int,
    default=1,
    metavar="QTY",
    help=(
      "Quantity of gifts to try to purchase on match "
      "(default: %(default)s)"
    )
  )
  args = parser.parse_args()
  
  filters = {
    "limited": True
  }
  if args.id is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set ID={args.id}")
    filters["id"] = args.id

  if args.title is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set TITLE={args.title}")
    filters["title"] = args.title.strip()

  if args.price is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set PRICE={args.price}")
    filters["price"] = args.price

  if args.total_amount is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set TOTAL_AMOUNT={args.total_amount}")
    filters["total_amount"] = args.total_amount

  async with app:
    me = await app.get_me()
    logger.warning(Fore.GREEN + Style.DIM + f"* Bot is connected to | {me.phone_number}:{me.username} |...\n")

    while True:
      try:
        gifts = await app.get_available_gifts()
        if filters.get("limited") is not None:
          gifts = filter(lambda g: g.is_limited == filters.get("limited"), gifts)
        
        if filters.get("title") is not None:
          gifts = filter(lambda g: g.raw.title == filters.get("title") or (args.nullable_title and g.raw.title is None), gifts)

        if filters.get("sold_out") is not None:
          gifts = filter(lambda g: g.is_sold_out == filters.get("sold_out"), gifts)

        if filters.get("id") is not None:
          gifts = filter(lambda g: g.id == filters.get("id"), gifts)

        if filters.get("price") is not None:
          gifts = filter(lambda g: g.price == filters.get("price"), gifts)

        if filters.get("total_amount") is not None:
          gifts = filter(lambda g: g.total_amount == filters.get("total_amount"), gifts)

        gifts = list(gifts)
        entries = len(gifts)
        if entries <= 0:
          logger.warning(Fore.RED + Style.DIM + f"Nothing found, waiting {args.check_every} secs...")
          await asyncio.sleep(args.check_every)
          continue
        
        gift = gifts[0]
        title = gift.raw.title
        t = f" \"{title}\"" if title is not None else ""
        message = f"Buying <b>{args.amount}</b>{t} gifts, estimated cost <b>{gift.price * args.amount}</b> stars...\n\n<span class=\"tg-spoiler\">ID: {gift.id}\nTITLE: {title}\nPRICE: {gift.price} stars\nTOTAL AMOUNT: {gift.total_amount}</span>"
        if entries > 1:
          logger.warning(Fore.YELLOW + Style.DIM + f"Found {entries} entries, using the first one")
          message = f"* <b>Warning: found {entries} entries, using the first one</b> *\n" + message

        msg_id = await tg_logger.send_gift_sticker(gift)        
        await tg_logger.send_message(message, reply_to_message_id=msg_id)
        return
      except Exception as e:
        tb_str = traceback.format_exc()
        logger.warning(f"err: {e} / {tb_str}")
    
if __name__ == "__main__":
  app.run(main())