TAB="    "

get_code_name() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '_'
}

get_autogenerate_notice() {
    generate_notice "#"
}

get_autogenerate_notice_html() {
    generate_notice "<!--" " -->"
}

generate_notice() {
    local comment_start=$1
    local comment_end=$2
    echo "\
$comment_start ============================================================================$comment_end\n\
$comment_start Author: Harry McKenzie${comment_end}\n\
$comment_start This file was autogenerated and should not be edited manually.$comment_end\n\
$comment_start Generated by script $0${comment_end}\n\
$comment_start ============================================================================$comment_end\n"
}

get_vox_column_value() {
    local extension="$1"
    local content="$2"
    echo "$content" | jq -r --arg ext "$extension" --arg column "$3" '.[] | select(.extension == $ext) | .[$column]'
}