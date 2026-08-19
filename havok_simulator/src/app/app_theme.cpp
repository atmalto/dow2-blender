#include "app_theme.h"

#include <QAbstractButton>
#include <QApplication>
#include <QCoreApplication>
#include <QDialogButtonBox>
#include <QEvent>
#include <QFileInfo>
#include <QIcon>
#include <QObject>
#include <QSize>
#include <QStyle>
#include <QStyleFactory>
#include <QWidget>

namespace
{
    class DialogButtonIconCleaner : public QObject
    {
    public:
        explicit DialogButtonIconCleaner(QObject* parent)
            : QObject(parent)
        {
        }

    protected:
        virtual bool eventFilter(QObject* watched, QEvent* event)
        {
            if (event && event->type() == QEvent::Show)
            {
                QDialogButtonBox* button_box = qobject_cast<QDialogButtonBox*>(watched);
                QWidget* widget = qobject_cast<QWidget*>(watched);

                if (button_box)
                {
                    clear_dialog_button_box_icons(button_box);
                }
                else if (widget)
                {
                    const QList<QDialogButtonBox*> button_boxes = widget->findChildren<QDialogButtonBox*>();
                    for (int index = 0; index < button_boxes.size(); ++index)
                    {
                        clear_dialog_button_box_icons(button_boxes[index]);
                    }
                }
            }

            return QObject::eventFilter(watched, event);
        }
    };

    QString find_media_file(const QString& file_name)
    {
        const QString candidates[] = {
            QCoreApplication::applicationDirPath() + "/../../media/" + file_name,
            QCoreApplication::applicationDirPath() + "/../media/" + file_name,
            QCoreApplication::applicationDirPath() + "/media/" + file_name,
            QString("media/") + file_name
        };
        int index = 0;

        for (index = 0; index < 4; ++index)
        {
            if (QFileInfo(candidates[index]).exists())
            {
                return candidates[index];
            }
        }

        return QString();
    }

    QString build_application_stylesheet(const QString& combo_chevron_path)
    {
        return QString(
            "QWidget {"
            "  background-color: #161a22;"
            "  color: #e5e9f0;"
            "}"
            "QMainWindow, QDialog {"
            "  background-color: #161a22;"
            "}"
            "QMenuBar {"
            "  background-color: #12161d;"
            "  border-bottom: 1px solid #252b35;"
            "}"
            "QMenuBar::item {"
            "  background: transparent;"
            "  padding: 6px 10px;"
            "  margin: 2px;"
            "  border-radius: 4px;"
            "}"
            "QMenuBar::item:selected {"
            "  background-color: #232a35;"
            "}"
            "QMenu {"
            "  background-color: #171d26;"
            "  border: 1px solid #2a313c;"
            "  padding: 4px;"
            "}"
            "QMenu::item {"
            "  padding: 6px 22px;"
            "  border-radius: 4px;"
            "}"
            "QMenu::item:selected {"
            "  background-color: #25303d;"
            "}"
            "QMenu::separator {"
            "  height: 1px;"
            "  background: #2a313c;"
            "  margin: 6px 8px;"
            "}"
            "QToolBar {"
            "  background-color: #12161d;"
            "  border-bottom: 1px solid #252b35;"
            "  spacing: 4px;"
            "  padding: 4px;"
            "}"
            "QStatusBar {"
            "  background-color: #12161d;"
            "  border-top: 1px solid #252b35;"
            "}"
            "QStatusBar::item {"
            "  border: 0px;"
            "}"
            "QLabel {"
            "  color: #d8dde7;"
            "}"
            "QPushButton, QToolButton {"
            "  background-color: #222a36;"
            "  color: #e8edf5;"
            "  border: 1px solid #394555;"
            "  border-radius: 4px;"
            "  padding: 5px 12px;"
            "}"
            "QPushButton:hover, QToolButton:hover {"
            "  background-color: #2b3441;"
            "  border-color: #465264;"
            "}"
            "QPushButton:pressed, QToolButton:pressed {"
            "  background-color: #1d232d;"
            "}"
            "QPushButton:disabled, QToolButton:disabled {"
            "  color: #7a8391;"
            "  background-color: #1b212a;"
            "  border-color: #252b35;"
            "}"
            "QLineEdit, QAbstractSpinBox, QComboBox {"
            "  background-color: #10151c;"
            "  color: #edf2f7;"
            "  border: 1px solid #2f3947;"
            "  border-radius: 4px;"
            "  padding: 4px 8px;"
            "  selection-background-color: #355070;"
            "}"
            "QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus {"
            "  border-color: #5b7c99;"
            "}"
            "QComboBox::drop-down {"
            "  subcontrol-origin: padding;"
            "  subcontrol-position: top right;"
            "  width: 20px;"
            "  border-left: 1px solid #2f3947;"
            "  background-color: #1c232d;"
            "  border-top-right-radius: 4px;"
            "  border-bottom-right-radius: 4px;"
            "}"
            "QComboBox::down-arrow {"
            "  image: url(%1);"
            "  width: 11px;"
            "  height: 7px;"
            "  margin-right: 6px;"
            "}"
            "QComboBox QAbstractItemView, QListView, QTreeView {"
            "  background-color: #171d26;"
            "  alternate-background-color: #171d26;"
            "  color: #edf2f7;"
            "  border: 1px solid #2f3947;"
            "  outline: 0px;"
            "  selection-background-color: #2c3b4b;"
            "  selection-color: #f7fbff;"
            "}"
            "QTreeView::item, QListView::item {"
            "  padding: 2px 4px;"
            "  border: 0px;"
            "}"
            "QTreeView::item:selected, QListView::item:selected {"
            "  background-color: #31506d;"
            "  color: #ffffff;"
            "}"
            "QHeaderView::section {"
            "  background-color: #1b212a;"
            "  color: #e5e9f0;"
            "  border: 0px;"
            "  border-bottom: 1px solid #2f3947;"
            "  padding: 4px 6px;"
            "}"
            "QTabWidget::pane {"
            "  border: 1px solid #2a313c;"
            "  background-color: #161a22;"
            "}"
            "QTabBar::tab {"
            "  background-color: #1b212a;"
            "  color: #d8dde7;"
            "  border: 1px solid #2a313c;"
            "  border-bottom: 0px;"
            "  border-top-left-radius: 4px;"
            "  border-top-right-radius: 4px;"
            "  padding: 6px 10px;"
            "  margin-right: 2px;"
            "}"
            "QTabBar::tab:selected {"
            "  background-color: #232a35;"
            "  color: #f7fbff;"
            "}"
            "QTabBar::tab:!selected {"
            "  margin-top: 2px;"
            "}"
            "QGroupBox {"
            "  border: 1px solid #2a313c;"
            "  border-radius: 4px;"
            "  margin-top: 12px;"
            "  padding-top: 12px;"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  left: 10px;"
            "  padding: 0 4px;"
            "  color: #f4f6fb;"
            "}"
            "QSlider {"
            "  min-height: 20px;"
            "}"
            "QSlider::groove:horizontal {"
            "  border: 0px;"
            "  height: 2px;"
            "  background: #0f141b;"
            "  border-radius: 999px;"
            "}"
            "QSlider::handle:horizontal {"
            "  background: #79a9d1;"
            "  border: 1px solid #9ac0e1;"
            "  width: 10px;"
            "  height: 10px;"
            "  margin: -4px 0;"
            "  border-radius: 999px;"
            "}"
            "QSlider::sub-page:horizontal {"
            "  background: #31506d;"
            "  border-radius: 999px;"
            "}"
            "QCheckBox, QRadioButton {"
            "  spacing: 6px;"
            "}"
            "QCheckBox::indicator, QRadioButton::indicator {"
            "  width: 14px;"
            "  height: 14px;"
            "}"
            "QScrollBar:vertical, QScrollBar:horizontal {"
            "  background: #12161d;"
            "  border: 0px;"
            "  margin: 0px;"
            "}"
            "QScrollBar::handle:vertical, QScrollBar::handle:horizontal {"
            "  background: #2c3643;"
            "  border-radius: 4px;"
            "  min-height: 20px;"
            "  min-width: 20px;"
            "}"
        ).arg(combo_chevron_path);
    }
}

void configure_application_theme(QApplication& app)
{
    QString combo_chevron_path = find_media_file("chevron-down.xpm");

    QStyle* app_style = QStyleFactory::create("Cleanlooks");
    if (!app_style)
    {
        app_style = QStyleFactory::create("Plastique");
    }
    if (app_style)
    {
        app.setStyle(app_style);
    }

    app.setStyleSheet(build_application_stylesheet(combo_chevron_path));
    app.installEventFilter(new DialogButtonIconCleaner(&app));
}

void clear_dialog_button_box_icons(QDialogButtonBox* button_box)
{
    QList<QAbstractButton*> buttons;
    int button_index = 0;

    if (!button_box)
    {
        return;
    }

    buttons = button_box->buttons();
    for (button_index = 0; button_index < buttons.size(); ++button_index)
    {
        if (buttons[button_index])
        {
            buttons[button_index]->setIcon(QIcon());
            buttons[button_index]->setIconSize(QSize(0, 0));
        }
    }
}
