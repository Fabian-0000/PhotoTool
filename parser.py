from pypdf import PdfReader
import math

# ----------------------------
# Matrix utilities
# ----------------------------
def multiply_matrices(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1*a2 + b1*c2,
        a1*b2 + b1*d2,
        c1*a2 + d1*c2,
        c1*b2 + d1*d2,
        e1*a2 + f1*c2 + e2,
        e1*b2 + f1*d2 + f2,
    )


def apply_matrix(m, x, y):
    a, b, c, d, e, f = m
    return (
        a*x + c*y + e,
        b*x + d*y + f,
    )


# ----------------------------
# Stream extraction
# ----------------------------
def get_stream_data(page):
    contents = page["/Contents"]

    if isinstance(contents, list):
        data = b"".join(obj.get_object().get_data() for obj in contents)
    else:
        data = contents.get_object().get_data()

    return data.decode("latin1")


# ----------------------------
# Rectangle detection
# ----------------------------
def is_axis_aligned_rect(points, tol=1e-2):
    if len(points) < 4:
        return False

    xs = sorted(set(round(p[0], 2) for p in points))
    ys = sorted(set(round(p[1], 2) for p in points))

    return len(xs) == 2 and len(ys) == 2

def process_stream(tokens, resources, ctm, fill_color, results):
    stack = []
    path = []

    i = 0
    while i < len(tokens):
        t = tokens[i]

        # --- Save state ---
        if t == "q":
            stack.append((ctm, fill_color))

        # --- Restore state ---
        elif t == "Q":
            ctm, fill_color = stack.pop()

        # --- Transform matrix ---
        elif t == "cm":
            try:
                vals = list(map(float, tokens[i-6:i]))
                ctm = multiply_matrices(ctm, tuple(vals))
            except:
                pass

        # --- RGB color ---
        elif t == "rg":
            try:
                r = float(tokens[i-3])
                g = float(tokens[i-2])
                b = float(tokens[i-1])
                fill_color = (r, g, b)
            except:
                pass

        # --- Grayscale ---
        elif t == "g":
            try:
                gray = float(tokens[i-1])
                fill_color = (gray, gray, gray)
            except:
                pass

        # --- Rectangle ---
        elif t == "re":
            try:
                x = float(tokens[i-4])
                y = float(tokens[i-3])
                w = float(tokens[i-2])
                h = float(tokens[i-1])

                p1 = apply_matrix(ctm, x, y)
                p2 = apply_matrix(ctm, x+w, y)
                p3 = apply_matrix(ctm, x+w, y+h)
                p4 = apply_matrix(ctm, x, y+h)

                path = [p1, p2, p3, p4]
            except:
                pass

        # --- Fill ---
        elif t in ("f", "f*", "B", "b"):
            if fill_color == (0.0, 0.0, 0.0):
                if is_axis_aligned_rect(path):
                    xs = [p[0] for p in path]
                    ys = [p[1] for p in path]

                    rect = (
                        min(xs),
                        min(ys),
                        max(xs),
                        max(ys),
                    )

                    x1, y1, x2, y2 = rect
                    x, y = x1, y1
                    w = x2 - x1
                    h = y2 - y1

                    results.append((x, y, w, h))

            path = []

        # --- XObject draw ---
        elif t == "Do":
            try:
                name = tokens[i-1]

                if "/XObject" in resources:
                    xobjects = resources["/XObject"]

                    if name in xobjects:
                        xobj = xobjects[name].get_object()

                        if xobj.get("/Subtype") == "/Form":
                            sub_ctm = ctm

                            # Apply XObject's own matrix if present
                            if "/Matrix" in xobj:
                                m = tuple(xobj["/Matrix"])
                                sub_ctm = multiply_matrices(ctm, m)

                            data = xobj.get_data().decode("latin1")
                            sub_tokens = data.replace("\n", " ").split()

                            sub_resources = xobj.get("/Resources", resources)

                            # RECURSION
                            process_stream(
                                sub_tokens,
                                sub_resources,
                                sub_ctm,
                                fill_color,
                                results,
                            )
            except Exception as e:
                pass

        i += 1

# ----------------------------
# Main parser
# ----------------------------
def extract_black_rectangle_rect(pdf_path):
    reader = PdfReader(pdf_path)
    results = []

    for page_num, page in enumerate(reader.pages):
        text = get_stream_data(page)
        tokens = text.replace("\n", " ").split()

        resources = page["/Resources"]

        process_stream(
            tokens,
            resources,
            ctm=(1, 0, 0, 1, 0, 0),
            fill_color=(0.0, 0.0, 0.0),  # default black
            results=results,
        )

    return results[0]