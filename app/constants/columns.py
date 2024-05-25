NON_EXACT_FLOAT_COLUMNS = ["col_r_", "col_p_", "col_v_"]

EXACT_FLOAT_COLUMNS = ["col_tp", "col_sl", "col_o", "col_p", "col_rr"]

EXACT_STRING_COLUMNS = ["col_d", "col_p", "col_t"]

REQUIRED_COLUMNS = ["note", "imgs"]


def get_mt_target_columns(mt_version):
    order_type = "type" if mt_version == "MT4_API" else "orderType"
    return [
        "ticket",
        "openTime",
        "closeTime",
        order_type,
        "lots",
        "symbol",
        "openPrice",
        "stopLoss",
        "takeProfit",
        "closePrice",
        "swap",
        "commission",
        "profit",
    ]


def get_mt_columns_rename(mt_version):
    order_type = "type" if mt_version == "MT4_API" else "orderType"
    return {
        "ticket": "#",
        "openTime": "col_d_Open Time",
        "closeTime": "col_d_Close Time",
        order_type: "col_m_Type",
        "lots": "col_m_Size",
        "symbol": "col_p",
        "openPrice": "col_o",
        "closePrice": "col_c",
        "stopLoss": "col_sl",
        "takeProfit": "col_tp",
        "commission": "col_m_Commision",
        "swap": "col_m_Swap",
        "profit": "col_v_Profit",
    }
