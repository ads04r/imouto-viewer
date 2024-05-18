from django.db import models

class Questionnaire(models.Model):
	label = models.CharField(max_length=255)
	description = models.TextField(default='', null=False)
	intro_text = models.TextField(default='', null=False)
	last_taken = models.DateTimeField(null=True, blank=True)
	random_order = models.BooleanField(default=False)
	enforce_answers = models.BooleanField(default=False)
	@property
	def question_count(self):
		return self.all_questions.count()
	@property
	def questions(self):
		if self.random_order:
			return self.all_questions.order_by('?')
		return self.all_questions.order_by('ordering')
	def create_question(self, question_text):
		if self.all_questions.count() == 0:
			new_id = 1
		else:
			new_id = self.all_questions.aggregate(x = models.Max('ordering'))['x'] + 1
		ret = QuestionnaireQuestion(question=question_text, ordering=new_id, questionnaire=self)
		ret.save()
		return ret
	def parse_request(self, post_data):
		ret = {}
		answered = []
		for kk in post_data.keys():
			k = str(kk)
			if not k.startswith('val'):
				continue
			question = self.all_questions.get(pk=k.replace('val', ''))
			answered.append(question.pk)
			answer = question.all_answers.get(pk=post_data[k])
			if not answer.reading_key in ret:
				ret[answer.reading_key] = 0
			ret[answer.reading_key] = ret[answer.reading_key] + answer.reading_value
		all_done = True
		if self.enforce_answers:
			for q in self.all_questions.all():
				if q.pk in answered:
					continue
				ret['missing'] = q.pk
				ret['answered'] = answered
				all_done = False
				break
		return {'status': all_done, 'results': ret}
	def __str__(self):
		return str(self.label)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'questionnaire'
		verbose_name_plural = 'questionnaires'

class QuestionnaireQuestion(models.Model):
	question = models.TextField()
	ordering = models.IntegerField()
	questionnaire = models.ForeignKey(Questionnaire, related_name='all_questions', on_delete=models.CASCADE)
	def create_answer(self, answer_text, reading_key, reading_value):
		if self.all_answers.count() == 0:
			new_id = 1
		else:
			new_id = self.all_answers.aggregate(x = models.Max('ordering'))['x'] + 1
		ret = QuestionnaireAnswer(answer=answer_text, ordering=new_id, question=self, reading_key=reading_key, reading_value=reading_value)
		ret.save()
		return ret
	@property
	def answers(self):
		return self.all_answers.order_by('ordering')
	def __str__(self):
		return str(self.question)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'questionnaire question'
		verbose_name_plural = 'questionnaire questions'

class QuestionnaireAnswer(models.Model):
	answer = models.TextField()
	ordering = models.IntegerField()
	question = models.ForeignKey(QuestionnaireQuestion, related_name='all_answers', on_delete=models.CASCADE)
	reading_key = models.SlugField(max_length=32)
	reading_value = models.IntegerField()
	def __str__(self):
		return str(self.answer)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'question answer'
		verbose_name_plural = 'question answers'
