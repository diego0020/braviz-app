function fold_one_answer(block){
var content = block.innerHTML
	function un_fold(){
	block.innerHTML = content
	}
block.innerHTML = '<a href="javascript:void(0)">Show Answer</a>'
block.firstChild.onclick = un_fold
}

function fold_all_answers(){
var answers = document.getElementsByTagName("blockquote");
for (var i = 0; i < answers.length ; i++ ){
fold_one_answer(answers.item(i))
}
// alert("ya")
}
window.onload = fold_all_answers;