#include "dialog_form_utils.h"

#include <QGridLayout>
#include <QLabel>
#include <QSlider>

namespace DialogFormUtils
{
    const float kPositionSliderScale = 0.1f;
    const float kRotationSliderScale = 0.1f;

    void assign_user_axes(float destination[3], float x_value, float y_value, float z_value)
    {
        destination[0] = x_value;
        destination[1] = z_value;
        destination[2] = y_value;
    }

    void extract_user_axes(const float source[3], float* x_value, float* y_value, float* z_value)
    {
        if (x_value)
        {
            *x_value = source[0];
        }
        if (y_value)
        {
            *y_value = source[2];
        }
        if (z_value)
        {
            *z_value = source[1];
        }
    }

    SliderRow add_slider_row(
        QGridLayout* layout,
        int row,
        const QString& text,
        int minimum,
        int maximum,
        int value,
        int tick_interval)
    {
        QLabel* label = new QLabel(text);
        QSlider* slider = new QSlider(Qt::Horizontal);
        QLabel* value_label = new QLabel();

        slider->setRange(minimum, maximum);
        slider->setValue(value);
        slider->setTickInterval(tick_interval);
        slider->setTickPosition(QSlider::TicksBelow);
        slider->setSingleStep(1);
        slider->setPageStep(tick_interval > 0 ? tick_interval : 1);

        layout->addWidget(label, row, 0);
        layout->addWidget(slider, row, 1);
        layout->addWidget(value_label, row, 2);

        SliderRow result;
        result.slider = slider;
        result.value_label = value_label;
        return result;
    }
}