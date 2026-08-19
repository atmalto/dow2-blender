#ifndef HAVOK_SCENE_APP_APP_THEME_H
#define HAVOK_SCENE_APP_APP_THEME_H

class QApplication;
class QDialogButtonBox;

void configure_application_theme(QApplication& app);
void clear_dialog_button_box_icons(QDialogButtonBox* button_box);

#endif
