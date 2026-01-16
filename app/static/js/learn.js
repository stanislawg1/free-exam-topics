let QUESTIONS = []
let TOPICS = []

function escapeHtml(unsafe) {
	if (unsafe === null || unsafe === undefined) return ''
	return String(unsafe)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;')
}

const topicSelect = document.getElementById('topic-select')
const questionSelect = document.getElementById('question-select')
const questionArea = document.getElementById('question-area')
const answerArea = document.getElementById('answer-area')
const commentsArea = document.getElementById('comments-area')
const prevBtn = document.getElementById('prev-q')
const showBtn = document.getElementById('show-btn')
const nextBtn = document.getElementById('next-q')

function populateTopics() {
	if (!topicSelect) return
	topicSelect.innerHTML = ''
	TOPICS.forEach(t => {
		const opt = document.createElement('option')
		opt.value = t
		opt.textContent = t
		topicSelect.appendChild(opt)
	})
}

function questionsForTopic(topic) {
	return QUESTIONS.filter(q => q.topic_number == topic)
}

function populateQuestions(topic) {
	if (!questionSelect) return
	const list = questionsForTopic(Number(topic))
	questionSelect.innerHTML = ''
	list.forEach(q => {
		const opt = document.createElement('option')
		opt.value = q.idx
		opt.textContent = q.question_number
		questionSelect.appendChild(opt)
	})
}

function renderQuestionByIdx(idx) {
	if (!questionArea) return
	const q = QUESTIONS.find(x => x.idx == idx)
	if (!q) return

	questionArea.innerHTML = q.question_html || ''

	const choices = q.choices || []
	const choicesContainer = document.createElement('div')
	choicesContainer.id = 'choices-container'

	if (choices.length) {
		const isMulti = q.correct_letters && q.correct_letters.length > 1
		choices.forEach(c => {
			const div = document.createElement('div')
			div.className = 'choice'
			const input = document.createElement('input')
			input.type = isMulti ? 'checkbox' : 'radio'
			input.name = 'answer'
			input.value = c.letter
			input.id = 'ch_' + c.letter
			const label = document.createElement('label')
			label.htmlFor = input.id
			label.innerHTML = `<strong>${c.letter}.</strong> ${c.text}`
			div.appendChild(input)
			div.appendChild(label)
			choicesContainer.appendChild(div)
			input.addEventListener('change', () => {
				handleAnswer(q.idx)
			})
		})
	} else {
		const hint = document.createElement('p')
		hint.style.marginTop = '0.5rem'
		hint.style.color = '#6b7280'
		hint.textContent = 'No choices for this question. Click "Show answer" below to reveal the suggested answer.'
		choicesContainer.appendChild(hint)
	}

	questionArea.appendChild(choicesContainer)

	if (commentsArea) commentsArea.innerHTML = ''
	if (answerArea) {
		answerArea.style.display = 'none'
		answerArea.innerHTML = ''
	}

	setButtonsState(false)

	if (showBtn) {
		const hasChoices = Array.isArray(choices) && choices.length > 0
		const hasImage = (q.question_html && q.question_html.indexOf('<img') !== -1) || (q.answer_html && q.answer_html.indexOf('<img') !== -1)
		if (hasChoices || hasImage) showBtn.classList.add('small-button')
		else showBtn.classList.remove('small-button')
	}
}

function revealAnswer(q) {
	if (!answerArea) return
	let html = ''
	const answerHtml = q.answer_html || ''
	html += `<p><strong>Suggested answer:</strong> ${answerHtml}</p>`

	if (q.voted_answers && q.voted_answers.length) {
		const items = q.voted_answers
			.map(v => {
				const letter = escapeHtml(v.voted_answers || v.answer || v.text || '')
				const votes = v.vote_count != null ? v.vote_count : v.votes != null ? v.votes : 0
				const star = v.is_most_voted ? ' ⭐' : ''
				return `<li><strong>${letter}</strong> <span class="meta">${votes} vote${votes != 1 ? 's' : ''}${star}</span></li>`
			})
			.join('')
		html += `<div class="voted-answers"><h4>Voted answers</h4><ul>${items}</ul></div>`
	}

	if (q.link) html += `<p style="margin-top:.5rem;"><a href="${q.link}" target="_blank">See this question on exam topics</a></p>`

	answerArea.innerHTML = html
	answerArea.style.display = 'block'
	highlightChoices(q.idx)
	renderComments(q.comments || [])
	if (showBtn) showBtn.classList.remove('small-button')
	setButtonsState(true)
}

function highlightChoices(idx) {
	const q = QUESTIONS.find(x => x.idx == idx)
	if (!q) return
	const selected = Array.from(document.querySelectorAll('#choices-container input[name="answer"]:checked')).map(i => i.value)
	const correct = q.correct_letters || []
	document.querySelectorAll('#choices-container .choice').forEach(div => {
		const label = div.querySelector('label')
		if (label) {
			label.style.background = 'transparent'
			label.style.borderColor = 'transparent'
		}
	})
	correct.forEach(letter => {
		const input = document.querySelector(`#ch_${letter}`)
		if (input) {
			const label = input.parentElement ? input.parentElement.querySelector('label') : document.querySelector(`label[for='ch_${letter}']`)
			if (label) label.style.background = '#dcfce7'
		}
	})
	selected.forEach(letter => {
		if (!correct.includes(letter)) {
			const input = document.querySelector(`#ch_${letter}`)
			if (input) {
				const label = input.parentElement ? input.parentElement.querySelector('label') : document.querySelector(`label[for='ch_${letter}']`)
				if (label) label.style.background = '#fee2e2'
			}
		}
	})
}

function handleAnswer(q_idx) {
	const q = QUESTIONS.find(x => x.idx == q_idx)
	if (!q) return
	const inputs = Array.from(document.querySelectorAll('#choices-container input[name="answer"]'))
	const selected = inputs.filter(i => i.checked).map(i => i.value)
	saveAnswer(q_idx, selected, false)

	const isMulti = q.correct_letters && q.correct_letters.length > 1
	if (!isMulti) {
		revealAnswer(q)
	}
}

function saveAnswer(q_idx, answers, shown) {
	const url = (window.LEARN_CONFIG && window.LEARN_CONFIG.learnSaveUrl) || '/'
	fetch(url, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ q_idx, answers, shown })
	})
		.then(r => r.json())
		.then(() => {})
		.catch(console.error)
}

function renderComments(comments) {
	if (!commentsArea) return
	commentsArea.innerHTML = ''
	if (!comments || !comments.length) return
	const h = document.createElement('h3')
	h.textContent = 'Comments'
	commentsArea.appendChild(h)
	comments.forEach(c => {
		const div = document.createElement('div')
		div.className = 'comment-entry'
		const meta = document.createElement('div')
		meta.className = 'comment-meta'
		const username = escapeHtml(c.username || 'anon')
		const date = c.date ? `<span class="sub"> ${escapeHtml(c.date)}</span>` : ''
		meta.innerHTML = `👤 ${username}${date}`
		const body = document.createElement('div')
		body.className = 'comment-body'
		body.textContent = c.content || ''
		div.appendChild(meta)
		div.appendChild(body)
		commentsArea.appendChild(div)
	})
}

function setButtonsState(shown) {
	if (!showBtn || !nextBtn || !prevBtn) return
	if (shown) {
		showBtn.classList.remove('start-button')
		showBtn.classList.add('prev-link')
		nextBtn.classList.remove('prev-link')
		nextBtn.classList.add('next-button')
	} else {
		showBtn.classList.remove('prev-link')
		showBtn.classList.add('start-button')
		nextBtn.classList.remove('next-button')
		nextBtn.classList.add('prev-link')
	}
}

function goToAdjacent(delta) {
	if (!questionSelect || !topicSelect) return
	const opts = Array.from(questionSelect.options)
	if (!opts.length) return
	let curQIdx = questionSelect.selectedIndex
	let newQIdx = curQIdx + delta
	if (newQIdx >= 0 && newQIdx < opts.length) {
		questionSelect.selectedIndex = newQIdx
		renderQuestionByIdx(Number(questionSelect.value))
		return
	}
	const topicOpts = Array.from(topicSelect.options)
	if (!topicOpts.length) return
	const curTopicIdx = topicSelect.selectedIndex
	const nextTopicIdx = (curTopicIdx + (delta > 0 ? 1 : -1) + topicOpts.length) % topicOpts.length
	topicSelect.selectedIndex = nextTopicIdx
	populateQuestions(Number(topicSelect.value))
	if (questionSelect.options.length) {
		questionSelect.selectedIndex = delta > 0 ? 0 : questionSelect.options.length - 1
		renderQuestionByIdx(Number(questionSelect.value))
	}
}

function onDataLoaded() {
	populateTopics()
	if (TOPICS.length) populateQuestions(TOPICS[0])
	if (topicSelect)
		topicSelect.addEventListener('change', () => {
			populateQuestions(topicSelect.value)
			if (questionSelect && questionSelect.options.length) {
				questionSelect.selectedIndex = 0
				renderQuestionByIdx(Number(questionSelect.value))
			}
		})
	if (questionSelect) questionSelect.addEventListener('change', () => renderQuestionByIdx(Number(questionSelect.value)))
	if (questionSelect && questionSelect.options.length) {
		questionSelect.selectedIndex = 0
		renderQuestionByIdx(Number(questionSelect.value))
	}
	if (showBtn) {
		showBtn.addEventListener('click', () => {
			const idx = Number(questionSelect.value)
			const q = QUESTIONS.find(x => x.idx == idx)
			if (q) {
				// When user explicitly asks to show the answer, save currently
				// selected choices (if any) and mark as shown.
				const inputs = Array.from(document.querySelectorAll('#choices-container input[name="answer"]'))
				const selected = inputs.filter(i => i.checked).map(i => i.value)
				saveAnswer(idx, selected.length ? selected : null, true)
				revealAnswer(q)
			}
		})
	}
	if (prevBtn) prevBtn.addEventListener('click', () => goToAdjacent(-1))
	if (nextBtn) nextBtn.addEventListener('click', () => goToAdjacent(1))
}

const dataUrl = (window.LEARN_CONFIG && window.LEARN_CONFIG.learnDataUrl) || '/'
fetch(dataUrl)
	.then(r => r.json())
	.then(data => {
		if (!data.ok) throw new Error(data.error || 'no data')
		QUESTIONS = data.questions || []
		TOPICS = data.topics || []
		onDataLoaded()
	})
	.catch(e => {
		if (questionArea) questionArea.innerHTML = `<p style="color:#b91c1c;">Failed to load questions: ${e.message}</p>`
		console.error(e)
	})


