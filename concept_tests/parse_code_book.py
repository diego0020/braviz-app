import os
from bs4 import BeautifulSoup

__author__ = 'Diego'

# Prerequisite: Export the codebook as an xhtml file using libre office (ms could produce a different xhtml structure)
# NOTE: consider using parse spss instead

def get_row_tokens(r):
    cols = r.find_all("span")
    text = map(lambda c:c.string,cols)
    return text

from braviz.readAndFilter import tabular_data

def send_to_db(var_name,var_desc,var_real,labels=None):
    #search database
    print var_name
    var_idx = tabular_data.get_var_idx(var_name)
    if var_idx is None:
        print "%s not in database"%var_name
        return
    db_desc = tabular_data.get_var_description(var_idx)
    if db_desc is None:
        print "Not description in db"
    else:
        print "From DB: %s"%db_desc
    print "From Codebook: %s"%var_desc
    #save code book description?
    #ans = raw_input("Save code book description [y/N]? ")
    #if ans.startswith("y"):
    #tabular_data.save_var_description(var_idx,var_desc)

    db_var_real = tabular_data.is_variable_real(var_idx)
    if db_var_real:
        print "DB: REAL"
    else:
        print "DB: NONIMAL"
    if var_real:
        print "CodeBook: REAL"
    else:
        print "CodeBook: NOMINAL"
        print "  labels: %s"%labels
    #save from codebook?
    #ans = raw_input("Save code book type [y/N]? ")
    #if ans.startswith("y"):
    #tabular_data.save_is_real(var_idx,var_real)
    #read again
    db_var_real = tabular_data.is_variable_real(var_idx)
    if not db_var_real:
        db_labels = tabular_data.get_labels_dict(var_idx)
        print "DB: %s"%db_labels
        if labels is  not None:
            print "CodeBook: %s"%labels
            #save from codebook?
            ans = raw_input("Save code book labels [y/N]? ")
            if ans.startswith("y"):
                pass
                #tabular_data.save_nominal_labels(var_idx,labels.items())


def parse_int(s):
    f = float(s.replace(",","."))
    return int(f)

def process_code_book():
    os.chdir("/home/diego/Downloads")
    with open("libro de codigos.xhtml") as html_file:
        soup = BeautifulSoup(html_file,"xml")

    tables = soup.find_all("table")
    for tab in tables:
        rows = tab.find_all("tr")
        var_name = get_row_tokens(rows[0])[0]
        desc_row = get_row_tokens(rows[3])
        var_des = desc_row[1]
        assert desc_row[0] == "Etiqueta"
        var_type_row=get_row_tokens(rows[6])
        assert var_type_row[-2]=="Medida"
        var_type = var_type_row[-1]
        #print "%s: \t %s"%(var_name,var_des)
        var_is_real = True
        if var_type in {"Ordinal","Nominal"}:
            var_is_real = False
            #find levels
            valid_values_rows = rows[8:]
            tokens = map(get_row_tokens,valid_values_rows)
            good_tokens = filter(lambda tok:tok[0]!="Valores perdidos",tokens)
            for tok in good_tokens:
                if tok[0].startswith("Valores"):
                    tok.pop(0)

            labels = dict(((parse_int(tok[-4]),tok[-3]) for tok in good_tokens if len(tok)==4))
            if len(labels) == 0:
                #likely mistake
                var_is_real = True
            if len(labels) > 20:
                #likely mistake
                var_is_real = True

        if not var_is_real:
            send_to_db(var_name,var_des,var_is_real,labels)
        else:
            send_to_db(var_name,var_des,var_is_real,None)

        print "=========================="

if __name__ == "__main__":
    process_code_book()

