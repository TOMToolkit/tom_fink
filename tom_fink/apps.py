from typing import Dict, List

from django.apps import AppConfig


class TomFinkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tom_fink"
    default = True  # tell Django that this is the AppConfig to use (when more than one are present)

    def data_services(self) -> List[Dict[str, str]]:
        """Add Fink to menu of DataServices available.

        This is the TOMToolkit integration point for including data services in the TOM.
        This method should return a list of dictionaries containing dot separated DataService classes.
        """
        return [{"class": f"{self.name}.fink.FinkDataService"}]
