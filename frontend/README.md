# Frontend (Flutter)

This folder will contain the Flutter app for Autograde (student and teacher views).

If Flutter is installed, generate the app here:

flutter create frontend

Then you can run:
- flutter run -d chrome
- flutter run -d linux (if set up)

Suggested initial pages:
- lib/main.dart: App shell with routing
- Student flow: subject selection -> question paper view -> PDF upload -> results view
- Teacher flow: upload question paper -> submissions list -> result correction -> publish
