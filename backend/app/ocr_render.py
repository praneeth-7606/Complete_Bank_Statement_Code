"""Render a masked PDF page with its real preceding table header for OCR retries.

Only geometry and header labels are inspected locally; transactions are always
read by Mistral. The header is copied as pixels, never synthesized.
"""
import fitz


def render_financial_columns(pdf_bytes, page_index):
    """Re-read amount columns as pixels, excluding narration/reference digits.

    Column boundaries come from printed headings, never from balance arithmetic.
    Returns None when the headings cannot be unambiguously located.
    """
    with fitz.open(stream=pdf_bytes, filetype='pdf') as source, fitz.open() as canvas:
        header = None
        for index in range(page_index, -1, -1):
            page = source[index]
            debit = [r for term in ('Debit', 'Withdrawal') for r in page.search_for(term)]
            credit = [r for term in ('Credit', 'Deposit') for r in page.search_for(term)]
            balances = page.search_for('Balance')
            candidates = [(d,c,b) for d in debit for c in credit for b in balances
                          if max(d.y0,c.y0,b.y0) - min(d.y0,c.y0,b.y0) < 5]
            if len(candidates) == 1:
                d,c,b = candidates[0]
                dates = [r for r in page.search_for('Date') if abs(r.y0-d.y0)<5]
                if not dates:
                    return None
                date = min(dates, key=lambda r:r.x0)
                first_amount = min(d.x0,c.x0,b.x0)
                amount_left = first_amount - min(abs(d.x0-c.x0),abs(c.x0-b.x0))/2
                date_right = date.x1 + max(25,date.width)
                if date_right >= amount_left:
                    return None
                header = (index, min(date.y0,d.y0,c.y0,b.y0)-5, max(date.y1,d.y1,c.y1,b.y1)+5,
                          date_right, amount_left)
                break
        if header is None:
            return None
        index, top, bottom, date_right, amount_left = header
        target = source[page_index]
        blocks = target.get_text('blocks')
        y0 = bottom if index == page_index else (max(0,min(b[1] for b in blocks)-10) if blocks else 0)
        y1 = min(target.rect.height,max(b[3] for b in blocks)+10) if blocks else target.rect.height
        header_height = bottom-top
        width = date_right + target.rect.width-amount_left
        output = canvas.new_page(width=width, height=header_height+y1-y0)
        # Left date strip and right financial strip preserve their vertical order.
        for source_index, start, end, dest_y in ((index,top,bottom,0),(page_index,y0,y1,header_height)):
            for x0,x1,dest_x in ((0,date_right,0),(amount_left,target.rect.width,date_right)):
                output.show_pdf_page(fitz.Rect(dest_x,dest_y,dest_x+x1-x0,dest_y+end-start),source,
                    source_index,clip=fitz.Rect(x0,start,x1,end))
        return output.get_pixmap(matrix=fitz.Matrix(3,3)).tobytes('png')


def render_page_context(pdf_bytes, page_index):
    with fitz.open(stream=pdf_bytes, filetype='pdf') as source, fitz.open() as canvas:
        target = source[page_index]
        header = None
        for index in range(page_index, -1, -1):
            page = source[index]
            debit = [r for term in ('Debit', 'Withdrawal') for r in page.search_for(term)]
            credit = [r for term in ('Credit', 'Deposit') for r in page.search_for(term)]
            balance = page.search_for('Balance')
            matched = [(d, c, b) for d in debit for c in credit for b in balance
                       if max(d.y0, c.y0, b.y0) - min(d.y0, c.y0, b.y0) < 5]
            if matched:
                if index != page_index:
                    boxes = matched[0]
                    header = (index, fitz.Rect(0, max(0, min(r.y0 for r in boxes) - 5), page.rect.width,
                                                min(page.rect.height, max(r.y1 for r in boxes) + 5)))
                break
        # Crop whitespace only on digital pages. For scans retain the full page.
        blocks = target.get_text('blocks')
        clip = target.rect
        if blocks and not target.get_images():
            clip = fitz.Rect(0, max(0, min(b[1] for b in blocks) - 20), target.rect.width,
                             min(target.rect.height, max(b[3] for b in blocks) + 20))
        header_height = header[1].height + 8 if header else 0
        output = canvas.new_page(width=target.rect.width, height=clip.height + header_height)
        if header:
            output.show_pdf_page(fitz.Rect(0, 0, target.rect.width, header[1].height), source,
                                 header[0], clip=header[1])
        output.show_pdf_page(fitz.Rect(0, header_height, target.rect.width, header_height + clip.height),
                             source, page_index, clip=clip)
        return output.get_pixmap(matrix=fitz.Matrix(3, 3)).tobytes('png')
