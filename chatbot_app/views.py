from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Prompt
from .serializers import PromptSerializer
from .llm import openai_instance, OpenaiModel


class PromptView(viewsets.ModelViewSet):
    queryset = Prompt.objects.all()
    serializer_class = PromptSerializer


@api_view(['GET'])
def chat_models(request):
    return Response({
        "models": OpenaiModel.choices()
    }, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
def chat(request):
    if request.method == 'POST':
        messages = request.data.get('messages')
        model_str = request.data.get('model')
        response = openai_instance.chat(model=OpenaiModel(model_str), messages=messages)
        return Response(response, status=status.HTTP_200_OK)
