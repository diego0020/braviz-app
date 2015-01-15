#!/bin/bash

test_if_has_bp () {
    local readonly boilerplate=license_boilerplate.txt
    local bp_text=$(cat $boilerplate)
    local file=$1
    local file_pre=$(cat $1 | head -n 18 )
    if [ "$bp_text" = "$file_pre" ] ; then
    echo "1"
    else
    echo "0"
    fi
}

remove_bp () {
local test=$( test_if_has_bp $1)
    if [ "$test" -eq "0" ]
    then
        echo removing bp from $1
        tail -n +18 > ${1}.nbp
        rm $1
        mv ${1}.nbp $1
    else
        echo $1 doesn't have bp
    fi
}

add_bp_to_file () {
    local test=$( test_if_has_bp $1)
    if [ "$test" -eq "0" ]
    then
        local boilerplate=license_boilerplate.txt
        local file=$1
        echo adding bolirplate to $file
        cat $boilerplate $file > ${file}.bp
        rm $file
        mv ${file}.bp $file
    else
        echo $1 already has boilerplate
    fi
}

add_to_braviz () {
    braviz_files=$(find ../braviz -name "*.py")
    for f in ${braviz_files[*]}
    do
        echo add to $f
        add_bp_to_file $f
        echo
    done


}

main () {
    readonly DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
    cd $DIR
    add_to_braviz

}

main