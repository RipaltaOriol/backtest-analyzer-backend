from enum import Enum

from app.models.Document import Document
from app.models.Setup import Setup
from app.models.User import User
from bson.json_util import dumps
from mongoengine.document import DynamicDocument, EmbeddedDocument
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


class ResultLearning(Enum):
    CORRECT = "Correct"
    UNKNOWN = "Unknown"
    INCORRECT = "Incorrect"


class EntryPosition(EmbeddedDocument):
    position_number = IntField(required=True)
    order_type = EnumField(OrderType, required=False)
    price = FloatField(required=False)
    risk = FloatField(required=False)
    size = FloatField(required=False)
    risk_reward = FloatField(required=False)


class TakeProfit(EmbeddedDocument):
    take_profit_number = IntField(required=True)
    take_profit = FloatField()


class Event(EmbeddedDocument):
    event_date = DateTimeField(required=True)
    monday = StringField(required=True, default="")
    tuesday = StringField(required=True, default="")
    wednesday = StringField(required=True, default="")
    thursday = StringField(required=True, default="")
    friday = StringField(required=True, default="")


class PPTTemplate(DynamicDocument):
    author = ReferenceField(User, reverse_delete_rule="CASCADE", required=True)
    document = ReferenceField(Document, required=True)
    setup = ReferenceField(Setup, reverse_delete_rule="CASCADE")  # , required=True)
    row_id = StringField(required=True)

    asset = StringField()
    direction = EnumField(Direction)

    base_ppt = EnumField(CurrencyReading)
    quote_ppt = EnumField(CurrencyReading)
    base_fundamental = EnumField(CurrencyReading)
    quote_fundamental = EnumField(CurrencyReading)
    reason = StringField()

    positions = ListField(EmbeddedDocumentField(EntryPosition), default=list)
    stop_loss = FloatField()
    take_profit = ListField(EmbeddedDocumentField(TakeProfit))

    current_price = FloatField()
    atr = StringField()
    retail_sentiment = StringField
    setup_comment = StringField()

    # MISSING some fields in here
    technical_levels = StringField()
    market_stucture = StringField()

    technical_analysis_comment = StringField()
    pre_trade_screenshot = StringField()
    tradingview_link = StringField()

    fundamental_risk = StringField()
    event_risk = StringField()
    event_risk_date = ListField(
        EmbeddedDocumentField(Event)
    )  # list of list used to track weekly events
    event_opportunity = StringField()
    event_opportunity_date = ListField(
        ListField(EmbeddedDocumentField(Event))
    )  # list of list used to track weekly events

    date_executed = DateTimeField()
    status = BooleanField()
    entry_alert = BooleanField()
    read_notes = BooleanField()
    is_stop_loss = BooleanField()
    is_take_profit = BooleanField()
    is_trade_placed = BooleanField()

    # MISSING some fields in here
    liquidity_levels = StringField()
    target_area = StringField()
    price_action = StringField()
    close_target_comment = StringField()
    close_reason = StringField()
    result = EnumField(Result)
    return_percentage = FloatField()
    return_value = FloatField()

    direction_result = EnumField(ResultLearning)
    levels_result = EnumField(ResultLearning)
    close_result = EnumField(ResultLearning)

    post_trade_screenshot = StringField()
    post_trade_comment = StringField()

    meta = {
        "collection": "ppttemplate",
        "ordering": ["-date_created"],
    }
