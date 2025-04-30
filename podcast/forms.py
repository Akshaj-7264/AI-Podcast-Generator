from django import forms

class PodcastForm(forms.Form):
    topic = forms.CharField(label='Enter Topic or Sentence', max_length=200)
