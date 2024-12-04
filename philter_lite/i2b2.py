from .philter import DataTracker


def save_to_i2b2(contents, output_file):
    with open(output_file, "w", errors="xmlcharrefreplace") as f:
        f.write(contents)


def transform_text_i2b2(tagdata: DataTracker):
    """Create a string in i2b2-XML format."""
    root = "Philter"
    contents = [
        '<?xml version="1.0" ?>\n',
        "<" + root + ">\n",
        "<TEXT><![CDATA[",
        tagdata.text,
        "]]></TEXT>\n",
        "<TAGS>\n",
    ]
    for i, phi in enumerate(tagdata.phi):
        phi_type = phi.phi_type
        contents.append("<")
        contents.append(phi_type)
        contents.append(' id="P')
        contents.append(str(i))
        contents.append('" start="')
        contents.append(str(phi.start))
        contents.append('" end="')
        contents.append(str(phi.stop))
        contents.append('" text="')
        contents.append(phi.word)
        contents.append('" TYPE="')
        contents.append(phi_type)
        contents.append('" comment="" />\n')

    # for loop over complement - PHI, create additional tags (UNKNOWN)
    contents.append("</TAGS>\n")
    contents.append("</" + root + ">\n")

    return "".join(contents)
