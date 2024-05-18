from app.models.Template import Template


class TemplateRepository:
    @staticmethod
    def get_template(name: str = "Default") -> Template:
        return Template.objects(name=name).first()
