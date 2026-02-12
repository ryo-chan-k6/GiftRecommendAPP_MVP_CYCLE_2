import { RegisterForm } from "../../../components/register/RegisterForm";

export default function AdminRegisterPage() {
  return <RegisterForm role="ADMIN" redirectPath="/" title="管理者登録" />;
}
