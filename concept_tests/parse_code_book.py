__author__ = 'Diego'
import os
from bs4 import BeautifulSoup

# Prerequisite: Export the codebook as an xhtml file using libre office (ms could produce a different xhtml structure)

os.chdir(r"C:\Users\Diego\Documents\kmc40-db\KAB-db")
with open("libro de codigos.xhtml") as html_file:
    soup = BeautifulSoup(html_file,"xml")

tables = soup.find_all("table")

def get_row_tokens(r):
    cols = r.find_all("span")
    text = map(lambda c:c.string,cols)
    return text

def parse_int(s):
    f = float(s.replace(",","."))
    return int(f)

for tab in tables:
    rows = tab.find_all("tr")
    var_name = get_row_tokens(rows[0])[0]
    desc_row = get_row_tokens(rows[3])
    var_des = desc_row[1]
    assert desc_row[0] == "Etiqueta"
    var_type_row=get_row_tokens(rows[6])
    assert var_type_row[-2]=="Medida"
    var_type = var_type_row[-1]
    print "%s: \t %s"%(var_name,var_des)
    if var_type in {"Ordinal","Nominal"}:
        print "NOMINAL"
        var_is_real = False
        #find levels
        valid_values_rows = rows[8:]
        tokens = map(get_row_tokens,valid_values_rows)
        good_tokens = filter(lambda tok:tok[0]!="Valores perdidos",tokens)
        for tok in good_tokens:
            if tok[0].startswith("Valores"):
                tok.pop(0)

        labels = [(parse_int(tok[-4]),tok[-3]) for tok in good_tokens if len(tok)==4]

        print labels

    else:
        var_is_real = True
        print "REAL"

    print "=========================="


