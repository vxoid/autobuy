from colorama import init, Fore, Style
from config import api_hash, api_id, logger_chat_id, logger_token
from pyrogram.errors.exceptions import StargiftUsageLimited
from pyrogram.types import Gift
from telegram import TGLogger
from pyrogram import Client
import traceback
import argparse
import asyncio
import logging
import math
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
    "--min-price",
    type=int,
    help=(
      "Only target gifts with exactly this or greater price"
      "(in TGStars)"
    )
  )
  parser.add_argument(
    "--max-price",
    type=int,
    help=(
      "Only target gifts with exactly this or less price"
      "(in TGStars)"
    )
  )
  parser.add_argument(
    "--total-amount",
    type=int,
    help=(
      "Only target gifts that have exactly this total available amount/supply"
    )
  )
  parser.add_argument(
    "--check-every",
    type=int,
    default=60,
    metavar="SECS",
    help=(
      "Poll for new gifts every N seconds "
      "(default: %(default)s)"
    )
  )
  parser.add_argument(
    "--star-amount",
    dest="star_amount",
    metavar="STARS",
    type=int,
    help=(
      "Amount of telegram stars you're willing to pay"
      "(alternative to --amount)"
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
    "limited": True,
    "sold_out": False,
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

  if args.min_price is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set MIN_PRICE={args.min_price}")
    filters["min_price"] = args.min_price

  if args.max_price is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set MAX_PRICE={args.max_price}")
    filters["max_price"] = args.max_price

  if args.total_amount is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set TOTAL_AMOUNT={args.total_amount}")
    filters["total_amount"] = args.total_amount
  
  if args.star_amount is not None:
    logger.warning(Fore.GREEN + Style.DIM + f"* set STAR_AMOUNT={args.star_amount} (skipping AMOUNT)")

  async with app:
    me = await app.get_me()
    star_balance = await app.get_stars_balance()
    logger.warning(Fore.GREEN + Style.DIM + f"* Bot is connected to | {me.phone_number}:{me.username} |: {star_balance} ⭐...\n")

    if args.star_amount is not None and args.star_amount > star_balance:
      logger.error(Fore.YELLOW + Style.DIM + f"* Insufficient balance.")
    
    remaining_balance = args.star_amount
    while True:
      try:
        gifts = await app.get_available_gifts()
        gifts = list(sorted(gifts, key=lambda g: float("inf") if g.total_amount is None else g.total_amount))

        if filters.get("limited") is not None:
          gifts = filter(lambda g: g.is_limited == filters.get("limited"), gifts)
        
        if filters.get("title") is not None:
            gifts = filter(
                lambda g: (getattr(g.raw, "title", None) == filters["title"]) or 
                          (args.nullable_title and getattr(g.raw, "title", None) is None),
                gifts
            )

        if filters.get("sold_out") is not None:
          gifts = filter(lambda g: g.is_sold_out == filters.get("sold_out"), gifts)

        if filters.get("id") is not None:
          gifts = filter(lambda g: g.id == filters.get("id"), gifts)

        if filters.get("price") is not None:
          gifts = filter(lambda g: g.price == filters.get("price"), gifts)

        if filters.get("min_price") is not None:
          gifts = filter(lambda g: g.price >= filters.get("min_price"), gifts)

        if filters.get("max_price") is not None:
          gifts = filter(lambda g: g.price <= filters.get("max_price"), gifts)

        if filters.get("total_amount") is not None:
          gifts = filter(lambda g: g.total_amount == filters.get("total_amount"), gifts)
        
        gifts = list(gifts)
        entries = len(gifts)
        if entries <= 0:
          logger.warning(Fore.RED + Style.DIM + f"Nothing found, waiting {args.check_every} secs...")
          await asyncio.sleep(args.check_every)
          continue
        
        if args.star_amount is None:
          gift = gifts[0]
          amount_succeeded = await buy_gift(me.id, gift, args.amount)

          total_amount = gift.price * amount_succeeded
          t = f" \"{gift.raw.title}\"" if gift.raw.title is not None else ""
          message = (
            f"<b>Completed</b>: sent <b>{amount_succeeded}</b> of <b>{args.amount}</b>{t} gifts\n"
            f"<b>Actual cost</b>: <b>{total_amount}</b> ⭐\n\n"
            f"<span class=\"tg-spoiler\">"
            f"ID: {gift.id}\n"
            f"TITLE: {gift.raw.title or 'untitled'}\n"
            f"PRICE: {gift.price} stars\n"
            f"TOTAL AMOUNT: {gift.total_amount or 'unlimited'}"
            f"</span>"
          )

          msg_id = await tg_logger.send_gift_sticker(gift)        
          await tg_logger.send_message(message, reply_to_message_id=msg_id)
          return

        tasks = []
        for gift in gifts:
          if gift.price > remaining_balance:
            continue
            
          a = math.floor(remaining_balance / gift.price)
          amount_succeeded = await buy_gift(me.id, gift, a)

          total_amount = gift.price * amount_succeeded
          remaining_balance -= total_amount
          t = f" \"{gift.raw.title}\"" if gift.raw.title is not None else ""
          message = (
            f"<b>Completed</b>: sent <b>{amount_succeeded}</b> of <b>{a}</b>{t} gifts\n"
            f"<b>Actual cost</b>: <b>{total_amount}</b> ⭐\n\n"
            f"<span class=\"tg-spoiler\">"
            f"ID: {gift.id}\n"
            f"TITLE: {gift.raw.title or 'untitled'}\n"
            f"PRICE: {gift.price} stars\n"
            f"TOTAL AMOUNT: {gift.total_amount or 'unlimited'}"
            f"</span>"
          )

          async def send():
            msg_id = await tg_logger.send_gift_sticker(gift)        
            await tg_logger.send_message(message, reply_to_message_id=msg_id)

          tasks.append(asyncio.create_task(send()))

        try:
          await asyncio.gather(*tasks)
        except Exception as e:
          tb_str = traceback.format_exc()
          logger.error(f"err: {e} / {tb_str}")
        return
      except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"err: {e} / {tb_str}")
    
async def buy_gift(receiver_id: int, gift: Gift, amount: int) -> int:
  i = 0   
  while True:
    if i >= amount:
      return i
    
    try: 
      await gift._client.send_gift(receiver_id, gift.id)
    except StargiftUsageLimited:
      logger.error(Fore.RED + f"Gift is sold out")
      return i
    except Exception as e:
      logger.error(f"send_gift err: {e}")
      return i
    
    i += 1

if __name__ == "__main__":
  app.run(main())