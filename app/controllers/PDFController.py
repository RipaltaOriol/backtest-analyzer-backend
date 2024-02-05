import io
import logging
import re
from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from app import app
from app.controllers.GraphsController import calculate_equity
from app.controllers.utils import from_db_to_df, parse_column_name, truncate
from app.models.Setup import Setup
from flask import Flask, make_response, send_file
from fpdf import FPDF, HTML2FPDF

matplotlib.use("Agg")
# plt.set_loglevel("info")


PAIR_COLUMN = "col_p"


class CustomHTML2FPDF(HTML2FPDF):
    pass


class PDF(FPDF):

    HTML2FPDF_CLASS = CustomHTML2FPDF

    def header(self):
        """Generates page header"""
        self.image("./imgs/logo.png", 10, 8, 8)
        self.set_font("arial", size=10)
        self.cell(80)
        self.cell(30, 10, "Report generated with Trade Sharpener", align="C")
        self.ln(20)

    def footer(self):
        """Generates page footer"""
        self.set_y(-15)
        self.set_font("arial", size=10)
        self.cell(0, 10, f"Page {self.page_no()} / {{nb}}", align="C")

    def write_html(self, text, image_map=None):
        h2p = HTML2FPDF(self, image_map)
        h2p.feed(text)

    def title_and_date(self, title):
        """Generates title and date section"""
        today = datetime.today().strftime("%d-%m-%Y")
        self.set_font("arial", size=20)
        self.cell(0, 10, txt=title)
        self.set_font("arial", size=12)
        self.cell(0, 10, txt=today, align="R", ln=1)

    def generate_notes_and_filters(self, notes: str, filters: List[str]) -> None:
        """Generates notes & filters section"""
        self.multi_cell(0, 5, txt=notes, ln=1)
        # TODO: create a bullet list
        for filter in filters:
            self.cell(0, 5, txt=filter.name, ln=1)

        if notes or filters:
            self.ln(10)

    def head1(self, txt: str) -> None:
        """Creates a header level 1"""
        self.start_section(txt, level=1)
        self.set_font("arial", size=16)
        self.cell(0, 10, txt=f"**{txt}**", markdown=True)
        self.ln(15)

    def head2(self, txt: str, ln: int = 15) -> None:
        """Creates a header level 2"""
        self.set_font("arial", size=14)
        self.cell(0, 10, txt=f"**{txt}**", markdown=True)
        self.ln(ln)

    def head3(self, txt: str) -> None:
        """Creates a header level 3"""
        self.set_font("arial", size=13)
        self.cell(0, 5, txt=f"--{txt}--", markdown=True)
        self.ln(7)

    def conditional_add_page(self):
        if self.get_y() > 30:
            self.add_page()

    def generate_trades_table(self, df) -> None:
        """Generates a trades table"""

        columns = [list(df)]  # get list of dataframe columns
        rows = df.values.tolist()  # get list of dataframe rows
        data = columns + rows  # combine columns and rows in one list
        self.set_font("arial", size=11)

        with self.table(
            cell_fill_color=(224, 224, 224),
            cell_fill_mode="ROWS",
            line_height=self.font_size * 2.5,
            text_align="CENTER",
        ) as table:
            for data_row in data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

    def trade_breakdown(self, row, results, metrics, add_page: bool) -> None:
        """Generate a breakdown for each individual trade passed in as a row"""
        self.set_font(style="U")
        trade_number = f" [{row.get('#', None)}]" if row.get("#", None) else ""
        self.head2(f"Trade: {row.get('col_p').upper()}{trade_number}", 5)
        self.ln(5)

        props = ["col_o", "col_sl", "col_c", "col_tp", "col_rr"] + results
        self.set_font("arial", size=12)

        is_left = True
        for prop in props:
            w = 100 if is_left else 0
            ln = 0 if is_left else 1
            self.cell(
                w,
                5,
                txt=f"\x95 {parse_column_name(prop)}: {row.get(prop, 'NA')}",
                ln=ln,
            )
            is_left = not is_left

        if is_left:
            self.ln(4)
        else:
            self.ln(8)

        self.head3("Metrics")
        self.set_font("arial", size=12)
        is_left = True
        for metric in metrics:
            w = 100 if is_left else 0
            ln = 0 if is_left else 1
            self.cell(
                w,
                5,
                txt=f"\x95 {parse_column_name(metric)}: {row.get(metric, 'NA')}",
                ln=ln,
            )
            is_left = not is_left

        if is_left:
            self.ln(4)
        else:
            self.ln(5)
        # replace <p> inside <li> tags with <span> otherwise it will cause a line break on <p>
        note_txt = re.sub(
            r"<li><p>(.*?)<\/p><\/li>", r"<li><span>\1</span></li>", row.get("note", "")
        )
        if note_txt:
            self.write_html(note_txt)
            self.ln(8)
        images = row.get("imgs", [])

        if images:  # images can be None occasionally
            for image in images:
                self.image(image, w=self.epw)
                self.ln(5)

        if add_page:
            self.conditional_add_page()


# TODO: make this funciton object oriented
def render_toc(pdf, outline):
    pdf.ln(10)
    pdf.set_font("Courier", size=12)
    pdf.underline = True

    pdf.cell(0, 5, "Table of Contents:", ln=2)
    pdf.underline = False
    for section in outline:
        link = pdf.add_link(page=section.page_number)
        pdf.cell(
            0,
            5,
            f'{" " * section.level * 1} {section.name} {"." * (70 - section.level*2 - len(section.name))} {section.page_number}',
            ln=2,
            link=link,
        )
    pdf.set_font("arial", size=14)
    pdf.cell(0, 10, txt=f"**Notes & Filters**", markdown=True)


# TODO: make it all of this a class
# TODO: prevent the pdf to be saved locally
def get_file(setup_id):

    try:
        # get setup
        setup = Setup.objects(id=setup_id).get()

        # create pdf & set font
        pdf = PDF(orientation="P", unit="mm", format="A4")
        pdf.set_font("Arial", size=12)

        pdf.add_page()
        title = f"{setup.documentId.name}: {setup.name}"

        pdf.title_and_date(title)
        # pdf.insert_toc_placeholder(render_toc) # renders table of contents
        pdf.head2("Notes & Filters")
        pdf.generate_notes_and_filters(setup.notes, setup.filters)

        pdf.head1("Trades Table")
        df = from_db_to_df(setup.state)

        # drop table columns
        df_drop_columns = [col for col in df.columns if col.startswith("col_m_")] + [
            "note",
            "imgs",
        ]

        # TODO: not sure why I do copy and then drop when I could just assign drop to the varialbe without inplace
        table_df = df.copy()

        table_df.drop(columns=df_drop_columns, inplace=True, errors="ignore")

        # stringify dates
        date_columns = [
            column for column in table_df.columns if re.match(r"col_d_", column)
        ]
        result_names = [
            column for column in df.columns if re.match(r"col_[vpr]_", column)
        ]
        for column in date_columns:
            table_df[column] = table_df[column].dt.strftime("%d/%m/%y")

        # transform pair to upper class
        if PAIR_COLUMN in df.columns:
            table_df[PAIR_COLUMN] = df[PAIR_COLUMN].str.upper()

        # truncates float
        truncate_columns = list(table_df.select_dtypes(include=["float64"]).columns)
        for column in truncate_columns:
            if column in result_names:
                table_df[column] = table_df[column].apply(lambda x: truncate(x, 2))
            else:
                table_df[column] = table_df[column].apply(lambda x: truncate(x, 5))

        df_rename_columns = {col: parse_column_name(col) for col in table_df.columns}
        reorder_columsn = (
            ["#", "col_p", "col_o", "col_sl", "col_tp"] + date_columns + result_names
        )
        table_df = table_df.reindex(reorder_columsn, axis=1).dropna(how="all", axis=1)
        table_df = table_df.rename(columns=df_rename_columns)

        table_df = table_df.applymap(str)

        pdf.generate_trades_table(table_df)

        pdf.conditional_add_page()

        pdf.head1("Equity Curve")
        generate_equity_curve(df, result_names, pdf)
        pdf.conditional_add_page()

        pdf.head1("Result Distribution")
        generate_result_distribution(df, result_names, pdf)
        pdf.conditional_add_page()

        pdf.head1("Trades Breakdown")
        metric_columns = [
            column for column in df.columns if re.match(r"col_m_", column)
        ]
        trades = setup.state.get("data").values()
        for i, trade in enumerate(trades):
            is_add_page = False if i == len(trades) - 1 else True
            pdf.trade_breakdown(
                trade, result_names, metric_columns, add_page=is_add_page
            )

        stream = io.BytesIO(pdf.output(dest="S"))
        return send_file(
            stream,
            mimetype="application/pdf",
            download_name=f"{title}.pdf",
            as_attachment=False,
        )

    except:
        # TODO: handle exception
        print("Something went wrong")

    # response = make_response(pdf.output(dest='S').encode('latin-1'))
    # response.headers.set('Content-Disposition', 'attachment', filename=title + '.pdf')
    # response.headers["Content-Type"] = "application/pdf"
    # return response


def generate_equity_curve(df: pd.DataFrame, result_names: List[str], pdf: FPDF) -> None:
    # TODO: this coult be moved to the FPDF class
    """
    Generate an equity curve of $10,000 based on the result names from the provided df (DataFrame).
    It prints the resuling graphs to the FPDF pdf object passed into the function.
    """

    plt.style.use("ggplot")
    plt.figure()

    for column in result_names:
        if column.startswith("col_v_"):
            method = "value"
        elif column.startswith("col_p_"):
            method = "percentage"
        elif column.startswith("col_r_"):
            method = "risk_reward"

        equity = 10000
        points = [equity]
        trades_amout = len(df[column])
        for i in range(trades_amout):
            equity = calculate_equity(equity, float(df[column].iloc[i]), method)
            points.append(equity)
        plt.plot(points, label=column[6:])

    plt.title("$10,000 Investment Simulation", fontsize=10)

    plt.legend()
    plt.grid(axis="x")
    plt.xlim(left=0, right=trades_amout)

    plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.gca().yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, p: "${0}".format(format(int(x), ",")))
    )

    img_buf = BytesIO()
    plt.savefig(img_buf, dpi=200)
    pdf.image(img_buf, w=pdf.epw)


def generate_result_distribution(
    df: pd.DataFrame, result_names: List[str], pdf: FPDF
) -> None:
    # TODO: this coult be moved to the FPDF class
    """
    Generate one of multiple pie charts based on the result distribution from the result names
    from the provided df (DataFrame). It prints the resuling graphs to the FPDF pdf object passed
    into the function.
    """

    plt.style.use("ggplot")
    pie_buf = BytesIO()

    if len(result_names) == 1:
        plt.figure()

        names, values = pie_result_distribution(df, result_names[0])
        p, tx, autotexts = plt.pie(values, labels=names, autopct="")

        for i, a in enumerate(autotexts):
            a.set_text("{}".format(values[i]))
        plt.title(result_names[0][6:] + " result distribution", fontsize=10)
        plt.savefig(pie_buf, dpi=200)

    else:
        fig, axs = plt.subplots(len(result_names), figsize=(10, 10))
        for i, result in enumerate(result_names):
            names, values = pie_result_distribution(df, result)
            p, tx, autotexts = axs[i].pie(values, labels=names, autopct="")

            for idx, a in enumerate(autotexts):
                a.set_text("{}".format(values[idx]))

            axs[i].set_title(result[6:] + " result distribution", fontsize=10)
            axs[i].legend()
        fig.savefig(pie_buf, dpi=200)

    pdf.image(pie_buf, w=pdf.epw)


def pie_result_distribution(
    df: pd.DataFrame, result_name: str
) -> Tuple[List[str], List[int]]:
    """
    Aggregates a given DataFrame from the provided result name. It returns a Tuple
    with the names (keys) and values from the aggregation.
    """
    result_agg = df[result_name].agg(
        {
            "Win": lambda s: s.gt(0).sum(),
            "Loss": lambda s: s.lt(0).sum(),
            "Break Event": lambda s: s.eq(0).sum(),
        }
    )
    data = dict(filter(lambda elem: elem[1] != 0, result_agg.items()))
    names = list(data.keys())
    values = list(data.values())
    return (names, values)
