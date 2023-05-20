from enum import Enum

from app.models.Document import Document
from app.models.Setup import Setup
from app.models.User import User
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    EmbeddedDocumentField,
    EnumField,
    FloatField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)


class Direction(Enum):
    LONG = "Long"
    SHORT = "Short"


class CurrencyReading(Enum):
    STRONG_BULLISH = "Strong Bullish"
    WEAK_BULLISH = "Weak Bullish"
    NEUTRAL = "Neutral"
    WEAK_BEARISH = "Weak Bearish"
    STRONG_BEARISH = "Strong Bearish"


class OrderType(Enum):
    MARKET = "Market"
    BUY_LIMIT = "Buy Limit"
    SELL_LIMIT = "Sell Limit"
    BUY_STOP = "Buy Stop"
    SELL_STOP = "Sell Stop"


class Result(Enum):
    WIN = "Win"
    LOSS = "Loss"
    BREAK_EVEN = "Break Even"


class EntryPosition(EmbeddedDocument):
    position_number = IntField(required=True)
    order_type = EnumField(OrderType, required=True)
    price = FloatField(required=True)
    risk = FloatField(required=True)
    size = FloatField(required=True)
    risk_reward = FloatField(required=True)


class TakeProfit(EmbeddedDocument):
    take_profit_number = IntField(required=True)
    take_profit = FloatField(required=True)


class Event(EmbeddedDocument):
    event_date = DateTimeField(required=True)
    event_risk = StringField(required=True)


# TODO: Investigate if you can modify a document
class PPTTemplate(Document):
    author = ReferenceField(User, reverse_delete_rule="CASCADE", required=True)
    document = ReferenceField(Document, reverse_delete_rule="CASCADE", required=True)
    setup = ReferenceField(Setup, reverse_delete_rule="CASCADE", required=True)
    row_id = StringField(required=True)

    asset = StringField(required=True)
    direction = EnumField(Direction, required=True)

    base_ppt = EnumField(CurrencyReading)
    quote_ppt = EnumField(CurrencyReading)
    base_fundamental = EnumField(CurrencyReading)
    quote_fundamental = EnumField(CurrencyReading)
    reason = StringField()

    positions = ListField(EmbeddedDocumentField(EntryPosition))
    stop_loss = FloatField()
    take_profit = ListField(EmbeddedDocumentField(TakeProfit))
    setup_comment = StringField()
    current_price = FloatField()

    # TODO: ask clarification about these fields
    # atr =
    # retail_sentiment =
    # MISSING technical levels (need clarification)
    pre_trade_screenshot = StringField()
    tradingview_link = StringField()
    technical_analysis_comment = StringField()

    fundamental_risk = StringField()
    event_risk = StringField()
    event_risk_date = ListField(ListField(EmbeddedDocumentField(Event)))
    event_opportunity = StringField()
    event_opportunity_date = ListField(ListField(EmbeddedDocumentField(Event)))

    date_executed = DateTimeField()
    # TODO: ask clarification about these fields
    # status =

    entry_alert = BooleanField()
    is_stop_loss = BooleanField()
    is_take_profit = BooleanField()
    is_trade_placed = BooleanField()

    # MISSING close levels (need clarification)
    close_reason = StringField()
    result = EnumField(Result)
    return_percentage = FloatField()
    return_value = FloatField()

    post_trade_screenshot = StringField()
    post_trade_comment = StringField()

    meta = {
        "collection": "ppttemplate",
        "ordering": ["-date_created"],
    }  # update meta data
