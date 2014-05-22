function fold_all_answers(){
var answers = document.getElementsByTagName("blockquote");
for (var i = 0; i < answers.length ; i++ ){
answers.item(i).innerHTML = "answer";
}
alert("ya")
}
// window.onload = fold_all_answers;