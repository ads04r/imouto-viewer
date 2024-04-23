from django.db import models

class Questionnaire(models.Model):
	label = models.CharField(max_length=255)
	last_taken = models.DateTimeField(null=True, blank=True)
	random_order = models.BooleanField(default=False)
	def __str__(self):
		return str(self.label)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'questionnaire'
		verbose_name_plural = 'questionnaires'

class QuestionnaireQuestion(models.Model):
	question = models.TextField()
	ordering = models.IntegerField()
	questionnaire = models.ForeignKey(Questionnaire, related_name='questions', on_delete=models.CASCADE)
	def __str__(self):
		return str(self.question)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'questionnaire question'
		verbose_name_plural = 'questionnaire questions'

class QuestionnaireAnswer(models.Model):
	answer = models.TextField()
	ordering = models.IntegerField()
	question = models.ForeignKey(QuestionnaireQuestion, related_name='answers', on_delete=models.CASCADE)
	reading_key = models.SlugField(max_length=32)
	reading_value = models.IntegerField()
	def __str__(self):
		return str(self.answer)
	class Meta:
		app_label = 'viewer'
		verbose_name = 'question answer'
		verbose_name_plural = 'question answers'
