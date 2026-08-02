import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NumericStepperInput } from "./OpportunitiesPage.jsx";

describe("NumericStepperInput", () => {
  it("renders stepper buttons and updates value", () => {
    const onChange = vi.fn();

    render(<NumericStepperInput value="" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: /increase/i }));
    expect(onChange).toHaveBeenCalledWith("1");

    fireEvent.click(screen.getByRole("button", { name: /decrease/i }));
    expect(onChange).toHaveBeenCalledWith("-1");
  });
});
