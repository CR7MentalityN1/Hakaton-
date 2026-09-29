export type Row = Record<string, any>;
export type Field = {
  key: string;
  label: string;
  type?: string;
  required?: boolean;
  options?: { id: string | number; name: string }[];
  disabled?: boolean;
};
