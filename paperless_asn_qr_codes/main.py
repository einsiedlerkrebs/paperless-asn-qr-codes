import argparse
import re

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab_qrcode import QRCodeImage

from paperless_asn_qr_codes import avery_labels


def render(c, x, y):
    global startASN
    global digits
    global simpleASN
    global tags
    global tag_prefix
    global line_length
    global max_lines
    max_chars_total = 0
    line_length = 0
    if not line_length:
        line_length = digits
    if simpleASN:
        human_asn_value = f"{startASN}"
    else:
        human_asn_value = f"ASN{startASN:0{digits}d}"

    if len(human_asn_value) > line_length:
        print(f"{human_asn_value} exceeds line width ({line_length} characters), tried -S option (simple-ASN)?")

    if tags:
        qr = QRCodeImage(f"ASN{startASN:0{digits}d},{tag_prefix}{f",{tag_prefix}".join(tags.split(','))}", size=y * 0.9)
    else:
        qr = QRCodeImage(f"ASN{startASN:0{digits}d}", size=y * 0.9)
    qr.drawOn(c, 0 * mm, y * 0.05)

    max_chars_total = (max_lines - 1) * line_length
    if not tags:
        starting_pos = (y - 2 * mm) / 2
    else:
        starting_pos = (y + 5 * mm) / 2

    tuned_pos = y + line_length - len(str(startASN))
    if len(str(startASN)) <= line_length:
        tuned_pos = y + line_length - len(str(startASN))
    c.setFont("Helvetica-Bold", 2 * mm)
    c.drawString(tuned_pos, starting_pos, human_asn_value)
    startASN = startASN + 1
    if not tags:
        return

    human_separator = ','
    tag_list = tags.split(human_separator)
    tag_char_sum = 0
    rows = []
    last_row = ""
    for tag in tag_list:
        if len(tag) + len(last_row) > max_chars_total:
            print(f"{tag=} exceeds total chars")
            continue
        if len(tag) > line_length:
            print(f"{tag=} exceeds line width ({line_length} characters)")
            continue
        elif len(tag) + len(last_row) + len(human_separator) > line_length:
            if len(rows) + 1 >= max_lines:
                print(f"{tag=} doesn't fit any more")
                continue
            else:
                rows.append(last_row)
                last_row = tag
        else:
            if last_row:
                last_row = f"{last_row}{human_separator}{tag}"
            else:
                last_row = tag

    rows.append(last_row)

    pos = 0
    for row in rows:
        c.setFont("Helvetica", 2 * mm)
        c.drawString(y-4, (y - pos * mm) / 2, row)
        pos = pos + 4






def main():
    # Match the starting position parameter. Allow x:y or n
    def _start_position(arg):
        if mat := re.match(r"^(\d{1,2}):(\d{1,2})$", arg):
            return (int(mat.group(1)), int(mat.group(2)))
        elif mat := re.match(r"^\d+$", arg):
            return int(arg)
        else:
            raise argparse.ArgumentTypeError("invalid value")
    # prepare a sorted list of all formats
    availableFormats = list(avery_labels.labelInfo.keys())
    availableFormats.sort()

    parser = argparse.ArgumentParser(
        prog="paperless-asn-qr-codes",
        description="CLI Tool for generating paperless ASN labels with QR codes",
    )
    parser.add_argument("start_asn", type=int, help="The value of the first ASN")
    parser.add_argument(
        "output_file",
        type=str,
        default="labels.pdf",
        help="The output file to write to (default: labels.pdf)",
    )
    parser.add_argument(
        "--format", "-f", choices=availableFormats, default="averyL4731"
    )
    parser.add_argument(
        "--digits",
        "-d",
        default=7,
        help="Number of digits in the ASN (default: 7, produces 'ASN0000001')",
        type=int,
    )
    parser.add_argument(
        "--border",
        "-b",
        action="store_true",
        help="Display borders around labels, useful for debugging the printer alignment",
    )
    parser.add_argument(
        "--row-wise",
        "-r",
        action="store_false",
        help="Increment the ASNs row-wise, go from left to right",
    )
    parser.add_argument(
        "--simple-ASN",
        "-S",
        action="store_true",
        help="Printed ASN is not prefixed by 'ASN' nor leading zeros",
    )
    parser.add_argument(
        "--tags",
        "-t",
        type=str,
        help="Comma separatored list of tags",
    )
    parser.add_argument(
        "--tag-prefix",
        "-T",
        type=str,
        default='TAG:',
        help="Serperator prefix for TAG_BARCODE_MAPPING",
    )
    parser.add_argument(
        "--num-labels",
        "-n",
        type=int,
        help="Number of labels to be printed on the sheet",
    )
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=1,
        help="Number of pages to be printed, ignored if NUM_LABELS is set (default: 1)",
    )
    parser.add_argument(
        "--start-position",
        "-s",
        type=_start_position,
        help="Define the starting position on the sheet, eighter as ROW:COLUMN or COUNT, both starting from 1 (default: 1:1 or 1)",
    )

    args = parser.parse_args()
    global startASN
    global digits
    global simpleASN
    global tags
    global tag_prefix
    global line_length
    global max_lines
    max_lines = 3
    tags = args.tags
    tag_prefix = args.tag_prefix
    startASN = int(args.start_asn)
    digits = int(args.digits)
    simpleASN = args.simple_ASN
    label = avery_labels.AveryLabel(
        args.format, args.border, topDown=args.row_wise, start_pos=args.start_position
    )
    label.open(args.output_file)

    # If defined use parameter for number of labels
    if args.num_labels:
        count = args.num_labels
    else:
        # Otherwise number of pages*labels - offset
        count = args.pages * label.across * label.down - label.position
    label.render(render, count)
    label.close()
