get_ppt_template_row = [
    {
        "$project": {
            "author": 1,
            "document": 1,
            "row_id": 1,
            "asset": 1,
            "direction": 1,
            "base_ppt": 1,
            "quote_ppt": 1,
            "base_fundamental": 1,
            "quote_fundamental": 1,
            "reason": 1,
            "positions": 1,
            "stop_loss": 1,
            "take_profit": 1,
            "current_price": 1,
            "atr": 1,
            "retail_sentiment": 1,
            "setup_comment": 1,
            "technical_levels": 1,
            "market_structure": 1,
            "technical_analysis_comment": 1,
            "pre_trade_screenshot": 1,
            "tradingview_link": 1,
            "fundamental_risk": 1,
            "event_risk": 1,
            "event_opportunity": 1,
            "status": 1,
            "entry_alert": 1,
            "read_notes": 1,
            "is_stop_loss": 1,
            "is_take_profit": 1,
            "is_trade_placed": 1,
            "liquidity_levels": 1,
            "target_area": 1,
            "price_action": 1,
            "close_target_comment": 1,
            "close_reason": 1,
            "result": 1,
            "return_percentage": 1,
            "return_value": 1,
            "direction_result": 1,
            "levels_result": 1,
            "close_result": 1,
            "post_trade_screenshot": 1,
            "post_trade_comment": 1,
            "date_executed": {
                "$dateToString": {
                    "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                    "date": "$date_executed",
                }
            },
            "event_risk_date": {
                "$map": {
                    "input": "$event_risk_date",
                    "as": "event_risk_date",
                    "in": {
                        "event_date": {
                            "$dateToString": {
                                "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                                "date": "$$event_risk_date.event_date",
                            }
                        },
                        "monday": "$$event_risk_date.monday",
                        "tuesday": "$$event_risk_date.tuesday",
                        "wednesday": "$$event_risk_date.wednesday",
                        "thursday": "$$event_risk_date.thursday",
                        "friday": "$$event_risk_date.friday",
                    },
                }
            },
            "success": True,
        }
    }
]
